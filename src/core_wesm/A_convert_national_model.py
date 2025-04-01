import otoole

input_folder = '../Kenya_national_model/'
input_file = 'data_smp_mod.txt' #update with the name of the data file

output_folder = '../National_parameter_model/'
output_file = 'data_smp_mod.xlsx' #update with the name of the output file

config_file = 'config_OSeMOSYS_Kenya.yaml'

otoole.convert(config_file, 'datafile', 'excel',
               input_folder+input_file, output_folder+output_file)

