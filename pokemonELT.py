import pymysql
import configparser
import csv

def readConfig(configFile):

    # Get credentials to connect to database
    config = configparser.ConfigParser()
    try:
        config.read_file(open(configFile)) # point to the correct place where this file is!
        dbConfig = {
            "host" : config['csc']['dbhost'],
            "user" : config['csc']['dbuser'],
            "password" : config['csc']['dbpw']
        }
        return dbConfig
    except FileNotFoundError as e:
        print(f"{configFile} was not found")
        raise

def connectToDatabase(dbName,configFile):

    #read in connection info
    dbConfig = readConfig(configFile)

    #Open database connection
    dbConn = pymysql.connect(host=dbConfig["host"],
                             user=dbConfig["user"],
                             passwd=dbConfig["password"],
                             db=dbName,
                             use_unicode=True,
                             charset='utf8mb4',
                             autocommit=True)

    return dbConn

def disconnectFromDatabase(dbConn):
    dbConn.close();

def processFile(fileName,dbConn):
    batchSize = 1
    with open(fileName) as pokemonFile:
        pokemonFileReader = csv.DictReader(pokemonFile)
        batchCounter = 1
        pokemonList = []
        for pokemonDictionary in pokemonFileReader:
            pokemonList.append(processRow(dbConn,pokemonDictionary))
            if(batchCounter == batchSize):
                pokemonList = []
                batchCounter = 1
            else:
                batchCounter += 1

def processRow(dbConn, pokemonDictionary):
    pokemonDictionary = cleanDictionary(pokemonDictionary)
    generationId = getGenerationDimension(dbConn, pokemonDictionary["Generation"])
    typeId1 = getTypeDimension(dbConn, pokemonDictionary["Type 1"])
    typeId2 = getTypeDimension(dbConn, pokemonDictionary["Type 2"])


    dataToInsert = (
        pokemonDictionary["ID#"], pokemonDictionary["Name"], pokemonDictionary["Legendary"], generationId,
        pokemonDictionary["HP"], pokemonDictionary["Attack"],
        pokemonDictionary["Defense"], pokemonDictionary["Sp. Atk"], pokemonDictionary["Sp. Def"], pokemonDictionary["Speed"],

    )
    savePokemonRow(dbConn, dataToInsert, typeId1, typeId2)

    return(
        pokemonDictionary["ID#"], pokemonDictionary["Name"], pokemonDictionary["Legendary"], generationId, pokemonDictionary["HP"],
        pokemonDictionary["Attack"], pokemonDictionary["Defense"], pokemonDictionary["Sp. Atk"], pokemonDictionary["Sp. Def"], pokemonDictionary["Speed"]

    )

def cleanDictionary(initialDictionary):
    # Convert empty strings to None in the row dictionary
    # return {key: (value if value != "" else None) for key, value in row.items()}
    cleanDictionary = {}
    for key,value in initialDictionary.items():
        if value == "":
            cleanDictionary[key] = None
        else:
            cleanDictionary[key] = value
    return cleanDictionary

def savePokemonRow(dbConn,dataToSave, type1, type2):
    pokemonInsertSQL= 'INSERT INTO pokemon ' \
                    '(pokedex_id, name, is_legendary, generation_id, hp, attack, defense, sp_attack, sp_defense, speed) ' \
                    'VALUES (%s, %s, %s ,%s, %s, %s, %s, %s, %s, %s);'
    typeInsertSQL = 'INSERT INTO pokemon_has_types (type_id, pokemon_id, slot) VALUES(%s, %s, %s)'
    print(dataToSave)

    cursor = dbConn.cursor()
    cursor.execute(pokemonInsertSQL,dataToSave)
    cursor.execute("SELECT LAST_INSERT_ID()")
    # Fetch the result
    pokemon_key = cursor.fetchone()[0]
    cursor.execute(typeInsertSQL,[type1, pokemon_key, 1])
    if(type2 is not None):
        cursor.execute(typeInsertSQL,[type2, pokemon_key, 2])

    cursor.close()


def getDimensionId(dbConn,dimensionSQL,dimensionLookupValue,dimensionIdColumn):
    print(f"Running {dimensionSQL}")
    print(f"With Value {dimensionLookupValue}")
    cursor = dbConn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(dimensionSQL,dimensionLookupValue)
    result = cursor.fetchone()
    cursor.close()
    if result is None:
        return None
    return result[dimensionIdColumn]

def insertDimension(dbConn,dimensionInsertSQL,dimensionInsertValue):
    print(f"Running {dimensionInsertSQL}")
    print(f"With Value {dimensionInsertValue}")
    cursor = dbConn.cursor()
    cursor.execute(dimensionInsertSQL,dimensionInsertValue)
    # Get the value of the auto-incremented key
    cursor.execute("SELECT LAST_INSERT_ID()")
    # Fetch the result
    auto_incremented_key = cursor.fetchone()[0]
    cursor.close()
    return auto_incremented_key

def getGenerationDimension(dbConn, generationValue):
    generationLookupSQL = "SELECT generation_id FROM pokemon_generation WHERE generation_num = %s"
    generationInsertSQL = "INSERT INTO pokemon_generation (generation_num) VALUES (%s)"
    generationId = mapSlowDimension(dbConn, generationLookupSQL, generationInsertSQL, generationValue, "generation_id")
    return generationId

def getTypeDimension(dbConn, typeValue):
    typeLookupSQL = "SELECT type_id FROM pokemon_types WHERE type_name = %s"
    typeInsertSQL = "INSERT INTO pokemon_types (type_name) VALUES (%s)"
    typeId = mapSlowDimension(dbConn, typeLookupSQL, typeInsertSQL, typeValue, "type_id")
    return typeId

def mapSlowDimension(dbConn,dimensionLookupSQL,dimensionInsertSQL,dimensionLookupValue,dimensionIdColumn):
    if dimensionLookupValue is None:
        return None
    dimensionId = getDimensionId(dbConn,dimensionLookupSQL,dimensionLookupValue,dimensionIdColumn)
    if dimensionId is None:
        dimensionId = insertDimension(dbConn,dimensionInsertSQL,dimensionLookupValue)
    return dimensionId

def mapStaticDimension(dbConn,dimensionLookupSQL,dimensionLookupValue,dimensionIdColumn):
    if dimensionLookupValue is None:
        return None
    dimensionId = getDimensionId(dbConn,dimensionLookupSQL,dimensionLookupValue,dimensionIdColumn)
    return dimensionId

#Start Main Program
if (__name__ == '__main__'):
    dbSchema = 'khoadley'
    configFile = 'credentials.txt'
    dataFile = 'Pokemon.csv'
    try:
        #1. Connect To Database
        dbConn = connectToDatabase(dbSchema,configFile)

        try:
            #2 Process the File
            processFile(dataFile,dbConn)

        except Exception as e:
            print(e)
        finally:
            # 3 Close DB Connection
            disconnectFromDatabase(dbConn)
    except Exception as e:
        print(e)