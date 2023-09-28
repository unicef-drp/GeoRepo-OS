#!/usr/bin/env bash
export_data=data.plt
export_dir=$(date +"%d-%m-%Y")
filename="${1##*/}"
filename="${filename%.*}"
mkdir -p "${export_dir}"
. "${1}" $export_data
gnuplot plot.p > "${export_dir}"/"${filename}".jpg
rm $export_data
