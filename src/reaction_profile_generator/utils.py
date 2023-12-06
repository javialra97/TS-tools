import os
from typing import Callable
from functools import wraps
from rdkit import Chem

ps = Chem.SmilesParserParams()
ps.removeHs = False


def work_in(dir_ext: list) -> Callable:
    """
    Decorator to execute a function in a different directory.

    Args:
        dir_ext (list: List containing subdirectory name to create or use.

    Returns:
        Callable: Decorated function.
    """

    def func_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):

            here = os.getcwd()
            dir_path = os.path.join(here, dir_ext[0])

            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)

            os.chdir(dir_path)
            try:
                result = func(*args, **kwargs)
            finally:
                os.chdir(here)

                if len(os.listdir(dir_path)) == 0:
                    os.rmdir(dir_path)

            return result

        return wrapped_function

    return func_decorator


def xyz_to_gaussian_input(xyz_file, output_file, method='UB3LYP', basis_set='6-31G(d,p)', extra_commands='opt=(calcfc,ts, noeigen) freq=noraman'):
    """
    Convert an XYZ file to Gaussian 16 input file format.

    Args:
        xyz_file (str): Path to the XYZ file.
        output_file (str): Path to the output Gaussian input file to be created.
        method (str, optional): The method to be used in the Gaussian calculation. Default is 'B3LYP'.
        basis_set (str, optional): The basis set to be used in the Gaussian calculation. Default is '6-31G(d)'.
    """
    filename = xyz_file.split('/')[-1].split('.xyz')[0]

    with open(xyz_file, 'r') as xyz:
        atom_lines = xyz.readlines()[2:]  # Skip the first two lines (number of atoms and comment)

    with open(output_file, 'w') as gaussian_input:
        # Write the route section
        if 'external' in method:
            gaussian_input.write(f'%Chk={filename}.chk\n# {method} {extra_commands}')
        else:
            gaussian_input.write(f'%Chk={filename}.chk\n%nproc=8\n%Mem=16GB\n# {method}/{basis_set} {extra_commands}')
        
        # Write the title section
        gaussian_input.write('\n\nTitle\n\n')

        # Write the charge and multiplicity section
        gaussian_input.write('0 1\n')

        # Write the Cartesian coordinates section
        for line in atom_lines:
            atom_info = line.split()
            element = atom_info[0]
            x, y, z = atom_info[1:4]
            gaussian_input.write(f'{element} {x} {y} {z}\n')

        # Write the blank line and the end of the input file
        gaussian_input.write('\n')

    print(f'Gaussian input file "{output_file}" has been created.')


def write_xyz_file_from_ade_atoms(atoms, filename):
    """
    Write an XYZ file from the ADE atoms object.

    Args:
        atoms: The ADE atoms object.
        filename: The name of the XYZ file to write.
    """
    with open(filename, 'w') as f:
        f.write(str(len(atoms)) + '\n')
        f.write('Generated by write_xyz_file()\n')
        for atom in atoms:
            f.write(f'{atom.atomic_symbol} {atom.coord[0]:.6f} {atom.coord[1]:.6f} {atom.coord[2]:.6f}\n')


def write_final_geometry_to_xyz(log_file_path):
    final_geometry = []
    reading_geometry = False
    after_transition_state_opt = False

    xyz_file_path = os.path.splitext(log_file_path)[0] + ".xyz"

    try:
        with open(log_file_path, 'r') as log_file:
            for line in log_file:
                if 'Stationary point found' in line:
                    after_transition_state_opt = True
                if after_transition_state_opt:
                    if 'Standard orientation' in line:
                        reading_geometry = True
                        final_geometry = []
                    elif reading_geometry:
                        # Lines with atomic coordinates are indented
                        columns = line.split()
                        if len(columns) == 6:
                            try:
                                atom_info = {
                                    'atom': int(columns[0]),
                                    'symbol': int(columns[1]),
                                    'x': float(columns[3]),
                                    'y': float(columns[4]),
                                    'z': float(columns[5])
                                }
                                final_geometry.append(atom_info)
                            except:
                                continue
                        else:
                            if len(final_geometry) != 0 and '-----------------------------' in line:
                                break

        if len(final_geometry) != 0:
            with open(xyz_file_path, 'w') as xyz_file:
                num_atoms = len(final_geometry)
                xyz_file.write(f"{num_atoms}\n")
                xyz_file.write("Final geometry extracted from Gaussian log file\n")
                for atom_info in final_geometry:
                    xyz_file.write(f"{atom_info['symbol']} {atom_info['x']:.6f} {atom_info['y']:.6f} {atom_info['z']:.6f}\n")

    except FileNotFoundError:
        print(f"File not found: {log_file_path}")
    
    return xyz_file_path


if __name__ == '__main__':
   write_final_geometry_to_xyz('logs/ts_guess_2.log')