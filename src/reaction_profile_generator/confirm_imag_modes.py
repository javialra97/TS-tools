from rdkit import Chem
import numpy as np
import autode as ade
import os
from scipy.spatial import distance_matrix
import re
from autode.species.species import Species
from typing import Optional
import shutil

xtb = ade.methods.XTB()


def validate_ts_guess(ts_file, path, factor=1.05, disp_cut_off=0.5, freq_cut_off=50, charge=0, final=False):
    """
    Validates a transition state guess by performing various checks on the provided parameters.

    Args:
        ts_file (str): The name of the (tentative) TS file.
        path (str): The path containing the reactant and product xyz-files.
        factor (float): Multiplication factor to apply to the equilibrium bond lengths for activation check. Defaults to 1.05.
        disp_cut_off (float): Cutoff value to filter small bond displacements. Defaults to 0.5.
        freq_cut_off (float): Cutoff value for the main imaginary frequency. Defaults to 50.
        charge (int, optional): The charge of the reacting system. Defaults to 0.
        final (bool, optional): Whether the TS guess is in its final form. Defaults to False.

    Returns:
        bool: True if the transition state is valid, False otherwise.

    This function validates a transition state (TS) guess by checking various criteria, including bond displacements, 
    bond directions, bond lengths, and frequency.

    Returns True if the TS is valid according to the checks and, optionally, 
    updates the TS guess if it's in its final form (final=True). Otherwise, it returns False.

    Note:
    - The factor parameter is used to adjust equilibrium bond lengths to check for activation.
    - The disp_cut_off parameter is used to filter small bond displacements.
    - The freq_cut_off parameter is a threshold for the main imaginary frequency.
    """
    # get all information about main imaginary mode
    freq, active_bonds_involved_in_mode, extra_bonds_involved_in_mode, \
    active_bonds_forming, active_bonds_breaking, reac_distances, prod_distances, \
    ts_distances = extract_info_ts_file(ts_file, path, charge, disp_cut_off)

    # determine which bonds, undergoing a change during the reaction, are active in the imaginary mode
    active_formed_bonds_involved_in_mode = [
        active_bonds_involved_in_mode[bond]
        for bond in set(active_bonds_involved_in_mode.keys()).intersection(active_bonds_forming)
    ]
    active_broken_bonds_involved_in_mode = [
        active_bonds_involved_in_mode[bond]
        for bond in set(active_bonds_involved_in_mode.keys()).intersection(active_bonds_breaking)
    ]

    #print(f'Main imaginary frequency: {freq} Active bonds in mode: {active_bonds_involved_in_mode};  Extra bonds in mode: {extra_bonds_involved_in_mode}')

    # Check that at least one active bond is getting displaced in mode,
    # check that all broken and formed bonds in the active mode move in the same direction,
    # and that the bond lengths are intermediate between reactants and products.
    bond_lengths_intermediate = check_if_bond_lengths_intermediate(ts_distances, reac_distances, prod_distances, 
                                                                    active_bonds_forming, active_bonds_breaking, factor)

    if len(extra_bonds_involved_in_mode) == 0 and len(active_bonds_involved_in_mode) != 0 \
    and check_same_sign(active_formed_bonds_involved_in_mode) \
    and check_same_sign(active_broken_bonds_involved_in_mode) and bond_lengths_intermediate and freq < - freq_cut_off:
        if final:
            move_final_guess_xyz(ts_file)
        return True
    else:
        return False


def determine_unactivated_bonds(ts_file, path, factor=1.05, disp_cut_off=0.5, charge=0):
    """
    Determine unactivated bonds in a transition state (TS) structure.

    Args:
        ts_file (str): The name of the TS file.
        path ():
        factor (float, optional): A factor to compare bond lengths with equilibrium lengths. Defaults to 1.05.
        disp_cut_off (float, optional): A cutoff value for filtering small bond displacements. Defaults to 0.5.
        charge (int, optional): The charge of the reacting system. Defaults to 0.


    Returns:
        list: A list of bond tuples that are unactivated in the TS structure.

    This function analyzes a TS structure and identifies unactivated bonds, 
    which are bonds that have not significantly deviated from their equilibrium lengths during the reaction. 
    It checks both bonds forming and bonds breaking during the reaction and compares their lengths to the equilibrium lengths
    adjusted by the factor parameter.

    Note:
    - The factor parameter is used to adjust equilibrium bond lengths for the activation check.
    - The disp_cut_off parameter is used to filter small bond displacements.
    """
    # get all information about main imaginary mode
    _, _, _, active_bonds_forming, active_bonds_breaking, \
    reac_distances, prod_distances, ts_distances = extract_info_ts_file(ts_file, path, charge, disp_cut_off)

    unactivated_bonds = []

    for active_bond in active_bonds_forming:
        if ts_distances[active_bond[0], active_bond[1]] < prod_distances[active_bond[0], active_bond[1]] * factor:
            unactivated_bonds.append(active_bond)
    
    for active_bond in active_bonds_breaking:
        if ts_distances[active_bond[0], active_bond[1]] < reac_distances[active_bond[0], active_bond[1]] * factor:
            unactivated_bonds.append(active_bond)    

    return unactivated_bonds


def check_if_bond_lengths_intermediate(ts_distances, reac_distances, prod_distances, active_bonds_forming, active_bonds_breaking, factor):
    """
    Checks if the bond lengths in the transition state are intermediate between reactants and products.

    Args:
        ts_distances (numpy.ndarray): Distance matrix of the transition state.
        reac_distances (numpy.ndarray): Distance matrix of the reactants.
        prod_distances (numpy.ndarray): Distance matrix of the products.
        active_bonds_forming (set): Set of active bonds involved in bond formation.
        active_bonds_breaking (set): Set of active bonds involved in bond breaking.
        factor (float): Multiplication factor to apply to the equilibrium bond lengths for activation check.

    Returns:
        bool: True if the bond lengths are intermediate, False otherwise.
    """

    for active_bond in active_bonds_forming:
        if ts_distances[active_bond[0], active_bond[1]] < prod_distances[active_bond[0], active_bond[1]] * factor:
            #print('forming: ', active_bond, ts_distances[active_bond[0], active_bond[1]], prod_distances[active_bond[0], active_bond[1]])
            return False
        else:
            continue
    
    for active_bond in active_bonds_breaking:
        if ts_distances[active_bond[0], active_bond[1]] < reac_distances[active_bond[0], active_bond[1]] * factor:
            #print('breaking: ', active_bond, ts_distances[active_bond[0], active_bond[1]], reac_distances[active_bond[0], active_bond[1]])
            return False
        else:
            continue
    
    return True


def check_same_sign(mode_list):
    """
    Checks if all numbers in the given list have the same sign.

    Args:
        mode_list (list): List of numbers.

    Returns:
        bool: True if all numbers have the same sign, False otherwise.
    """

    first_sign = 0

    for num in mode_list:
        if num > 0:
            sign = 1
        else:
            sign = -1

        if first_sign == 0:
            first_sign = sign
        elif sign != 0 and sign != first_sign:
            return False
        
    return True


def move_final_guess_xyz(ts_guess_file):
    """
    Moves the final transition state guess XYZ file to a designated folder and renames it.

    Args:
        ts_guess_file (str): Path to the transition state guess XYZ file.

    Returns:
        None
    """

    path_name = '/'.join(os.getcwd().split('/')[:-1])
    reaction_name = os.getcwd().split('/')[-1]
    shutil.copy(ts_guess_file, os.path.join(path_name, 'final_ts_guesses'))
    os.rename(
        os.path.join(os.path.join(path_name, 'final_ts_guesses'), ts_guess_file.split('/')[-1]), 
        os.path.join(os.path.join(path_name, 'final_ts_guesses'), f'{reaction_name}_final_ts_guess.xyz')
    )


def extract_info_ts_file(ts_file, path, charge, cut_off=0.5):
    """
    Extract information related to a transition state (TS) from a directory.

    Args:
        ts_file (str): The directory containing TS files.
        path (str): The path containing the reactant and product xyz-files.
        charge (int): The charge of the system.
        cut_off (float, optional): A cutoff value to filter bond displacements. Defaults to 0.5.

    Returns:
        tuple: A tuple containing the following information:
            - float: Frequency of the TS.
            - dict: Active bonds involved in the imaginary mode, with bond indices as keys and displacement values as values.
            - dict: Extra bonds involved in the imaginary mode, with bond indices as keys and displacement values as values.
            - set: Active bonds forming during the TS.
            - set: Active bonds breaking during the TS.
            - numpy.ndarray: Distance matrix for reactant molecules.
            - numpy.ndarray: Distance matrix for product molecules.
            - numpy.ndarray: Distance matrix for the TS geometry.

    This function analyzes the provided TS directory to determine if it represents an imaginary mode and extracts various relevant information, 
    including bond displacements, active bonds forming and breaking, and distance matrices for the reactants, products, and TS geometry.

    Note:
    - The bond displacement cutoff (cut_off) is used to filter small bond displacements. 
        Bonds with displacements below this threshold are ignored.
    """
    # Obtain reactant, product, and transition state molecules
    reactant_file, product_file = get_xyzs(path)
    reactant, product, ts_mol = get_ade_molecules(reactant_file, product_file, ts_file, charge)   

    # Compute the displacement along the imaginary mode
    normal_mode, freq = read_first_normal_mode(os.path.join(path, 'g98.out'))
    f_displaced_species = displaced_species_along_mode(ts_mol, normal_mode, disp_factor=1)
    b_displaced_species = displaced_species_along_mode(reactant, normal_mode, disp_factor=-1)

    # Compute distance matrices -- reactants, products and tentative TS
    reac_distances = distance_matrix(reactant.coordinates, reactant.coordinates)
    prod_distances = distance_matrix(product.coordinates, product.coordinates)
    ts_distances = distance_matrix(ts_mol.coordinates, ts_mol.coordinates)

    # Compute distance matrices -- TS geometry obtained through displacement along imaginary mode
    f_distances = distance_matrix(f_displaced_species.coordinates, f_displaced_species.coordinates)
    b_distances = distance_matrix(b_displaced_species.coordinates, b_displaced_species.coordinates)

    # Compute delta_mode
    delta_mode = f_distances - b_distances

    # Get all the bonds in both reactants and products
    all_bonds = set(product.graph.edges).union(set(reactant.graph.edges))

    # Identify active forming and breaking bonds
    active_bonds_forming = set(product.graph.edges).difference(set(reactant.graph.edges))
    active_bonds_breaking = set(reactant.graph.edges).difference(set(product.graph.edges))
    active_bonds = active_bonds_forming.union(active_bonds_breaking)

    # Determine active bonds and extra bonds involved in the mode
    active_bonds_involved_in_mode = {}
    extra_bonds_involved_in_mode = {}

    # Check bond displacements and assign involvement
    for bond in all_bonds:
        if bond in active_bonds: 
            if abs(delta_mode[bond[0], bond[1]]) < 2 * cut_off:
                continue  # Small displacement, ignore
            else:
                active_bonds_involved_in_mode[bond] = delta_mode[bond[0], bond[1]]
        else:
            if abs(delta_mode[bond[0], bond[1]]) < cut_off:
                continue  # Small displacement, ignore
            else:
                extra_bonds_involved_in_mode[bond] = delta_mode[bond[0], bond[1]] 

    return freq, active_bonds_involved_in_mode, extra_bonds_involved_in_mode, active_bonds_forming, \
        active_bonds_breaking, reac_distances, prod_distances, ts_distances


def truncate_line_list_log_file(lines):
    """
    Truncate lines from a Gaussian log file.

    Parameters:
    lines (list of str): Lines from a Gaussian log file.

    Returns:
    list of str: Truncated lines with normal mode information.
    """
    ts_found = None
    for idx, line in enumerate(lines):
        if '-- Stationary point found.' in line:
            ts_found = idx
        if ts_found is not None and 'Harmonic frequencies (cm**-1)' in line:
            return lines[idx:]


def read_first_normal_mode(filename, log_file=False):
    """
    Read the first normal mode from the specified file.

    Args:
        filename (str): The name of the file to read.
        log_file (bool): Whether the file containing the frequencies is a gaussian output file or not.

    Returns:
        numpy.ndarray: Array representing the normal mode.
        float: Frequency value.
    """
    normal_mode = []
    pattern = r'\s+(\d+)\s+\d+\s+([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)'

    # Open the file and read its contents
    with open(filename, 'r') as file:
        lines = file.readlines()
        # if log-file, then first determine where the frequency block starts
        if log_file:
            lines = truncate_line_list_log_file(lines)
        # Iterate over the lines and find the matching pattern
        for line in lines:
            # Check if the line contains a frequency
            if 'Frequencies' in line:
                # Extract the frequency value from the line
                frequency = float(line.split('--')[1].split()[0])

                # Iterate over the lines below the frequency line
                if log_file:
                    offset = 5
                else:
                    offset = 7
                for sub_line in lines[lines.index(line) + offset:]:
                    # Check if the line matches the pattern
                    match = re.search(pattern, sub_line)
                    if match:
                        x = float(match.group(2))
                        y = float(match.group(3))
                        z = float(match.group(4))
                        normal_mode.append([x, y, z])
                    else:
                        break
                break

    return np.array(normal_mode), frequency


def displaced_species_along_mode(
    species: Species,
    normal_mode = np.array,
    disp_factor: float = 1.0,
    max_atom_disp: float = 99.9,
) -> Optional[Species]:
    """
    Displace the geometry along a normal mode with mode number indexed from 0,
    where 0-2 are translational normal modes, 3-5 are rotational modes and 6
    is the largest magnitude imaginary mode (if present). To displace along
    the second imaginary mode we have mode_number=7

    ---------------------------------------------------------------------------
    Arguments:
        species (autode.species.Species):
        mode_number (int): Mode number to displace along

    Keyword Arguments:
        disp_factor (float): Distance to displace (default: {1.0})

        max_atom_disp (float): Maximum displacement of any atom (Å)

    Returns:
        (autode.species.Species):

    Raises:
        (autode.exceptions.CouldNotGetProperty):
    """
    coords = species.coordinates
    disp_coords = coords.copy() + disp_factor * normal_mode

    # Ensure the maximum displacement distance any single atom is below the
    # threshold (max_atom_disp), by incrementing backwards in steps of 0.05 Å,
    # for disp_factor = 1.0 Å
    for _ in range(20):

        if (
            np.max(np.linalg.norm(coords - disp_coords, axis=1))
            < max_atom_disp
        ):
            break

        disp_coords -= (disp_factor / 20) * normal_mode

    # Create a new species from the initial
    disp_species = Species(
        name=f"{species.name}_disp",
        atoms=species.atoms.copy(),
        charge=species.charge,
        mult=species.mult,
    )
    disp_species.coordinates = disp_coords

    return disp_species


def get_ade_molecules(reactant_file, product_file, ts_guess_file, charge):
    """
    Load the reactant, product, and transition state molecules.

    Args:
        reactant_file (str): The name of the reactant file.
        product_file (str): The name of the product file.
        ts_guess_file (str): The name of the transition state guess file.

    Returns:
        ade.Molecule: Reactant molecule.
        ade.Molecule: Product molecule.
        ade.Molecule: Transition state molecule.
    """
    reactant = ade.Molecule(reactant_file, charge=charge)
    product = ade.Molecule(product_file, charge=charge)
    ts = ade.Molecule(ts_guess_file, charge=charge)

    return reactant, product, ts


def get_xyzs(path):
    """
    Get the names of the reactant and product files.

    Args:
        path (str): The path to workdir with the xyz-files.

    Returns:
        str: The name of the reactant file.
        str: The name of the product file.
    """
    print(path)
    reactant_file = [f for f in os.listdir() if f == 'conformer_reactant_init_optimised_xtb.xyz'][0]
    product_file = [f for f in os.listdir() if f == 'conformer_product_init_optimised_xtb.xyz'][0]

    return os.path.join(path, reactant_file), os.path.join(path, product_file)
