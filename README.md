# TS-tools

This is the repository corresponding to the TS-tools project.

### Setting up the environment

To set up the ts-tools conda environment:

```
conda env create -f environment.yml
```

To install the TS-tools package, activate the ts-tools environment and run the following command within the TS-tools directory:

```
conda activate ts-tools
pip install .
```

Additionally, Gaussian16 needs to be available. In HPC environments, this can typically be achieved by loading the corresponding module to the path:

```
module load gaussian/g16_C01
```

Finally, the xTB path in the external xtb script needs to be adapted to the local settings (L13 in 'xtb/external_script/xtb_external.py')

### Generating TS guesses at xTB level-of-theory

TS guesses at xTB level of theory can be generated by running the following command (individual calculations are run in parallel as a single Python ProcessPool):

```
python run_scripts/run_ts_searcher.py [--input-file data/reactions_am.txt] [--xtb-external-path xtb_external_script/xtb_external.py]
```

where the ’input-file’ command line option corresponds to the location of the .txt-file containing the reaction SMILES (the default value ’reactions_am.txt’ corresponds to the benchmarking reactions), and the ’xtb-external-path’ option corresponds to the location of the script to use xTB as an external method in Gaussian16 (copied from the Jensen group's [xtb_gaussian](https://github.com/jensengroup/xtb_gaussian/blob/main/xtb_external.py) repository).  

Additional options can also be provided:

1. '--reactive-complex-factors-intra': Specifies a list of floating-point numbers representing reactive complex factors for intra-molecular interactions.
2. '--reactive-complex-factors-inter': Specifies a list of floating-point numbers representing reactive complex factors for inter-molecular interactions.
3. '--solvent': Specifies the name of the solvent (needs to be supported in xTB, e.g., 'water')
4. '--freq-cut-off': Specifies the imaginary frequency cut-off used during filtering of plausible starting points for transition state guess optimization.
5. '--target-dir': Specifies the working directory in which all files will be saved; final reactant, product and TS guess geometries (as well as the TS .log file) are saved in another directory with the ’final_’ prefix.

Upon execution of this script, a work directory is first set up (named 'work_dir' by default), and for every reaction, a separate sub directory is generated. In each of these sub directory, 'path_dir' contains all the files produced during the generation of the reactive complex(es) and path(s). The preliminary guesses derived from the reactive paths are saved in 'preliminary_ts_guesses'. 'rp_geometries' in its turn contains the start- and end-points of the reactive path, 'g16_dir' contains all the files associated with the TS optimizations -- and IRC confirmations -- of the preliminary guesses, and 'final_ts_guess' contains the xyz- and log-file of the final confirmed TS (if found). Upon completion of the workflow for all reactions in the input file, the contents of 'final_ts_guess' and 'rp_geometries' is copied to the specified target_dir. 

### Validating TS guesses at DFT level of theory  

Validating TS guesses at xTB level-of-theory can be done by running the following command (individual calculations are run in parallel as a single Python ProcessPool):

```
python run_scripts/dft_validation.py [--input-file data/reactions_am.txt] [--input-dir final_work_dir]
``` 

where the ’input-file’ command line option corresponds to the location of the .txt-file containing the reaction SMILES (the default value ’reactions_am.txt’ corresponds to the benchmarking reactions),
and the ’input-dir’ command line option corresponds to the location of the folder in which the final TS guess geometries have been saved (see previous section).

Additional options can also be provided:

1. '--solvent': Specifies the name of the solvent (needs to be supported both in Gaussian16, e.g., 'water')
2. '--output-dir': Specifies the working directory in which all files will be saved (default is 'validation_dir').
3. '--mem': Specifies the memory requested in the Gaussian16 .com files (default is '16GB')
4. '--proc': Specifies the number of processors requested in the Gaussian16 .com files (default is 8) 
5. '--functional': Specifies the functional to be used for the DFT calculations (default is 'UB3LYP')
6. '--basis-set': Specifies the basis set to be used for the DFT calculations (default is '6-31G**')

Upon execution of this script, the specified output directory is created, as well as sub directories for each reaction SMILES in the input file. In each of these sub directories, 'rp_geometries' contains the xyz-files of reactants and products, and 'g16_dir' contains the files associated with the TS optimization -- and IRC confirmations -- of the xTB level TS determined during the original TS search (see previous section). The final DFT level TS geometry is saved in the latter directory as well, under the same name as the original xyz-file in the input directory. 

### Generating TS guesses at DFT level of theory

TS guesses at DFT level-of-theory (from an xTB reactive path) can be generated by running the following command (individual calculations are run in parallel as a single Python ProcessPool):

```
python run_scripts/run_ts_searcher_dft.py [--input-file data/reactions_am.txt] [--xtb-external-path xtb_external_script/xtb_external.py]
```

where the ’input-file’ command line option corresponds to the location of the .txt-file containing the reaction SMILES (the default value ’reactions_am.txt’ corresponds to the benchmarking reactions),
and the ’xtb-external-path’ option corresponds to the location of the script to use xTB as an external method in Gaussian16 (copied from the Jensen group's [xtb_gaussian](https://github.com/jensengroup/xtb_gaussian/blob/main/xtb_external.py) repository).
Note that this script will be a lot slower than xTB optimization of TSs, and should consequently only be used when full xTB level-of-theory TS guess generation fails.

Additional options can also be provided:

1. '--reactive-complex-factors-intra': Specifies a list of floating-point numbers representing reactive complex factors for intra-molecular interactions.
2. '--reactive-complex-factors-inter': Specifies a list of floating-point numbers representing reactive complex factors for inter-molecular interactions.
3. '--solvent': Specifies the name of the solvent to be used in both the xTB and DFT calculations
4. '--xtb_solvent': Specifies the name of the solvent to be used in the xTB calculations (only needed when universal 'solvent' keyword is not specified)
5. '--dft_solvent': Specifies the name of the solvent to be used in the DFT calculations (only needed when universal 'solvent' keyword is not specified)
6. '--freq-cut-off': Specifies the imaginary frequency cut-off used during filtering of plausible starting points for transition state guess optimization.
7. '--target-dir': Specifies the working directory in which all files will be saved; final reactant, product and TS guess geometries (as well as the TS .log file) are saved in another 
directory with the ’final_’ prefix.
8. '--mem': Specifies the memory requested in the Gaussian16 .com files (default is '16GB')
9. '--proc': Specifies the number of processors requested in the Gaussian16 .com files (default is 8)
10. '--functional': Specifies the functional to be used for the DFT calculations (default is 'UB3LYP')
11. '--basis-set': Specifies the basis set to be used for the DFT calculations (default is '6-31G**')

Upon execution of this script, work and output directories are set up in the same manner as for the xTB script (respectively named 'work_dir_dft' and 'final_work_dir_dft' by default).

### References

If (parts of) this workflow are used as part of a publication, please cite the associated paper:

```
@article{stuyver2024,
  author       = {Stuyver, T.},
  title        = {{TS-tools: Rapid and Automated Localization of 
Transition States based on a Textual Reaction SMILES Input}},
  journal      = {ChemRxiv},
  year         = {2024},
  doi          = {10.26434/chemrxiv-2024-st2tr},
}
``` 

Furthermore, since the workflow makes use of autodE at several instances, also consider citing the paper in which this code was originally presented:

```
@article{autodE,
  doi = {10.1002/anie.202011941},
  url = {https://doi.org/10.1002/anie.202011941},
  year = {2021},
  publisher = {Wiley},
  volume = {60},
  number = {8},
  pages = {4266--4274},
  author = {Tom A. Young and Joseph J. Silcock and Alistair J. Sterling and Fernanda Duarte},
  title = {{autodE}: Automated Calculation of Reaction Energy Profiles -- Application to Organic and Organometallic Reactions},
  journal = {Angewandte Chemie International Edition}
}
```

