set -e

SCRIPT_PATH=`dirname $0`


error_exit() {
    echo "$1" 1>&2
    exit 1
}



copy_ext() {
    
    local source=$1
    local target=$2
    local permission=$3
    local user=$4
    local group=$5
    if ! cp $source $target; then
        error_exit "Can not copy ${source} to ${target}"
    fi
    if ! chmod -R $permission $target; then
        error_exit "Can not do chmod ${permission} for ${target}"
    fi
    if ! chown $user:$group $target; then
        error_exit "Can not do chown ${user}:${group} for ${target}"
    fi
    echo "cp_ext: ${source} -> ${target} chmod ${permission} & chown ${user}:${group}"
}

is_leader() {
    
    
    
    
    
    
    
    if [[ "$EB_IS_COMMAND_LEADER" == "true" ]]; then
        
        
        
        true
    else
        
        
        
        false
    fi
}

script_add_line() {
    local target_file=$1
    local check_text=$2
    local add_text=$3

    if grep -q "$check_text" "$target_file"
    then
        echo "Modification ${check_text} found in ${target_file}"
    else
        echo ${add_text} >> ${target_file}
        echo "Modification ${add_text} added to ${target_file}"
    fi
}
