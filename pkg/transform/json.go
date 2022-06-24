package transform

import (
	"fmt"
	"log"
	"strconv"
	"strings"
)

func JSONList(srcList []map[string]interface{}, keyMap map[string]string) []map[string]interface{} {
	transformed := []map[string]interface{}{}

	for _, item := range srcList {
		destination := map[string]interface{}{}

		for sourceKey, destinationKey := range keyMap {
			keys := strings.Split(destinationKey, ".")

			lastID := len(keys) - 1
			level := map[string]interface{}{}
			for id, key := range keys {
				if lastID == id {
					level[key] = getValue(sourceKey, item)
				} else {
					destination[key] = map[string]interface{}{}
					level = destination[key].(map[string]interface{})
				}
			}
		}
		transformed = append(transformed, destination)
	}

	return transformed
}

func getValue(key string, m map[string]interface{}) string {
	keys := strings.Split(key, ".")
	for _, current := range keys {
		if _, ok := m[current]; !ok {
			return "" // should be err?
		}

		switch m[current].(type) {
		case string:
			return m[current].(string)
		case map[string]interface{}:
			m = m[current].(map[string]interface{})
		case int, int64:
			i := m[current].(int)
			return strconv.Itoa(i)
		case float32, float64:
			f := m[current].(float64)
			return fmt.Sprintf("%f", f)
		default:
			log.Println("Wat is this")
			return ""
		}
	}

	return ""
}
