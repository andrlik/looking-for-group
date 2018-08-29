#! /usr/bin/env bash

PRODUCTION_FILE='requirements.txt'
DEV_FILE='test_requirements.txt'
usage="$(basename "$0") [-h/--help] [-p FILENAME] [-d FILENAME] -- Program to sync pipenv lockfile to pip-compatible requirements.

where:
     -h/--help Show this help text
     -p FILENAME Specify what file should be used for production packages (default: requirements.txt)
     -d FILENAME Specify what file should be used for development packages (default: test_requirements.txt)
     -D Skip creating file of dev/test requirements
     -l Lock/pin the versions (note, VCS packages will always be pinned.)
"
lock=false
while [ ! $# -eq 0 ]
do
    shift_twice=true
    case "$1" in
        --help | -h)
            echo "$usage"
            exit
            shift_twice=false
            ;;
        -p )
            PRODUCTION_FILE="$2"
            ;;
        -d )
            DEV_FILE="$2"
            ;;
        -D )
            DEV_FILE=""
            ;;
        -l )
            lock=true
            shift_twice=false
            ;;
        * )
            echo "You have specified an invalid option."
            echo "$usage"
            exit 1
            ;;
    esac
    if [ "$shift_twice" = true ];then
        shift
        shift
    else
        shift
    fi
done


echo "Starting sync of Pipenv to pip-compatible requirements..."
echo "-------------"
if [ "$PRODUCTION_FILE" != "requirements.txt" ]; then
    echo "Using production file of ${PRODUCTION_FILE}."
fi
echo "Syncing production requirement packages..."
if [ "$lock" = true ];then
    echo "Pinning requirements..."
    pipenv lock --requirements | grep -v "#" | cut -d' ' -f1 | grep -v "^\-i$" > $PRODUCTION_FILE
else
    pipenv lock --requirements | grep -v "#" | sed 's/==.*//' | grep -v "^\-i " > $PRODUCTION_FILE
fi
echo "Syncing production VCS packages..."
pipenv lock --requirements | grep "#" | sed 's/# //' >> $PRODUCTION_FILE
echo "Finished production packages!"

echo "--------------"
if [ ! $DEV_FILE ]; then
    echo "Skipping development file."
else
    if [ "$DEV_FILE" != "test_requirements.txt" ]; then
        echo "Using development file of ${DEV_FILE}."
    fi
    echo "Syncing dev requirement packages..."
    if [ "$lock" = true ];then
        echo "Pinning requirements..."
        pipenv lock --dev --requirements | grep -v "#" | cut -d' ' -f1 | grep -v "^\-i$" > $DEV_FILE
    else
        pipenv lock --dev --requirements | grep -v "#" | sed 's/==.*//' | grep -v "^\-i " > $DEV_FILE
    fi
    echo "Syncing dev VCS packages..."
    pipenv lock --dev --requirements | grep "#" | sed 's/# //' >> $DEV_FILE
    echo "Finished dev packages!"
fi
echo "--------------"
echo "Done!"
