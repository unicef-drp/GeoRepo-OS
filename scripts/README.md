# GeoRepo Benchmark Scripts

## Requirements

Install apache benchmark (ab) from apache2 utils package.

```
apt-get install apache2-utils
```

## Environment variables

Copy export_var.template.sh to export_var.sh and replace the values.

```
cp export_var.template.sh export_var.sh
```

Find the values from Module, Dataset, and View from GeoRepo Django Admin page.
You also need to provide entity's concept ucode and ucode for this tests which you can find from GeoRepo Dataset Detail/View Preview page.

You can also configure the number of requests and concurrencies that ab will use using variables: NUM_OF_REQUESTS and NUM_OF_CONCURRENCIES.

## Running the scripts

The request files are numbered and you need to use **run_benchmark.sh** script to run each file.
Load the environment variables before running the sripts.

```
source export_var.sh
./run_benchmark.sh 01_module_list.sh
./run_benchmark.sh 02_dataset_list.sh
```

The benchmark results will be in the output directory with date format (DD-MM-YYYY).
