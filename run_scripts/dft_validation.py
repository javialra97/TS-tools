import time
import os
import multiprocessing
import concurrent.futures
import argparse
import shutil

from reaction_profile_generator.ts_optimizer import TSOptimizer
from reaction_profile_generator.utils import setup_dir, get_reaction_list, print_statistics


def get_args():
    """
    Parse command line arguments.

    Returns:
    - argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--solvent', action='store', type=str, default=None)
    parser.add_argument('--input-file', action='store', type=str, default='test_aldol.txt')
    parser.add_argument('--input-dir', action='store', type=str, default='final_test_aldol')
    parser.add_argument('--output-dir', action='store', type=str, default='validation_dir')

    return parser.parse_args()


def validate_individual_ts(validation_args):
    """
    Validate a transition state using the given validation arguments.

    Parameters:
    - validation_args (tuple): A tuple containing the transition state optimizer
      and the input directory path.

    Returns:
    - str: The reaction ID if the transition state is validated, False otherwise.
    """
    ts_validated = False
    ts_guess_file = None
    ts_optimizer, input_dir_path = validation_args
    guess_dir_path = os.path.join(input_dir_path, f'final_outputs_reaction_{ts_optimizer.rxn_id}')
    ts_optimizer.path_dir = guess_dir_path
    ts_optimizer.final_guess_dir = ts_optimizer.reaction_dir

    try:
        for file in os.listdir(guess_dir_path):
            if 'ts_guess' in file and file.endswith('.xyz'):
                ts_guess_file = os.path.join(guess_dir_path, file)
            elif file == 'reactants_geometry.xyz':
                shutil.copy(os.path.join(guess_dir_path, file), ts_optimizer.rp_geometries_dir)
            elif file == 'products_geometry.xyz':
                shutil.copy(os.path.join(guess_dir_path, file), ts_optimizer.rp_geometries_dir)
    except Exception as e:
        print(e)

    if ts_guess_file is not None:
        ts_optimizer.modify_ts_guess_list([ts_guess_file])
        try:
            ts_validated = ts_optimizer.determine_ts(xtb=False)
        except Exception as e:
            print(e)
            pass
    
    if ts_validated:
        #for file in os.listdir(ts_optimizer.g16_dir):
        #    if 'reverse' not in file and 'forward' not in file:
        #        if file.endswith('.xyz') or file.endswith('.log'):
        #            shutil.copy(file, ts_optimizer.reaction_dir)
        return ts_optimizer.rxn_id
    
    return False


def validate_ts_guesses(input_dir, output_dir, reaction_list, solvent):
    """
    Validate transition state guesses for a list of reactions.

    Parameters:
    - input_dir (str): Input directory.
    - output_dir (str): Output directory.
    - reaction_list (list): List of tuples containing reaction indices and SMILES strings.
    - solvent (str): Solvent information.

    Returns:
    - list: List of validated reaction IDs.
    """
    home_dir = os.getcwd()
    input_dir_path = os.path.join(os.getcwd(), input_dir)
    ts_optimizer_list = []
    os.chdir(output_dir)

    for rxn_idx, rxn_smiles in reaction_list:
        ts_optimizer_list.append([
            TSOptimizer(rxn_idx, rxn_smiles, None, solvent=solvent, guess_found=True),
            input_dir_path
        ])

    os.chdir(home_dir)

    print(f'{len(ts_optimizer_list)} reactions to process...')

    num_processes = multiprocessing.cpu_count()

    with concurrent.futures.ProcessPoolExecutor(max_workers=int(num_processes/2)) as executor:
        # Map the function to each object in parallel
        results = list(executor.map(validate_individual_ts, ts_optimizer_list))

    validated_reactions = [r for r in results if r is not None]

    os.chdir(home_dir)

    return validated_reactions


if __name__ == "__main__":
    # preliminaries
    args = get_args()
    reaction_list = get_reaction_list(args.input_file)
    setup_dir(args.output_dir)
    start_time = time.time()

    validated_reactions = validate_ts_guesses(args.input_dir, args.output_dir, reaction_list, args.solvent)

    print_statistics(validated_reactions, start_time)
