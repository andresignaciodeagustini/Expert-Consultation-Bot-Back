from typing import Dict, List, Any

# Nuevos patrones de idioma para detección y procesamiento
NEW_LANGUAGE_PATTERNS = {
    # Idiomas europeos occidentales
    'nl': {  # Holandés
        'pattern': r'[àáèéëïòóôöùÀÁÈÉËÏÒÓÔÖÙ]',
        'keywords': ['punt', 'onderstreping', 'email', 'apenstaart', 'koppelteken'],
        'common_domains': ['nl', 'amsterdam', 'rotterdam'],
        'email_terms': {
            'dot': ['punt', 'punten'],
            'underscore': ['onderstreping', 'laag streepje'],
            'at': ['apenstaart', 'at'],
            'hyphen': ['koppelteken', 'streepje'],
            'dash': ['streep', 'gedachtestreep']
        }
    },
    
    'pl': {  # Polaco
        'pattern': r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]',
        'keywords': ['kropka', 'podkreślenie', 'małpa', 'kreska'],
        'common_domains': ['pl', 'warszawa', 'krakow'],
        'email_terms': {
            'dot': ['kropka', 'punkt'],
            'underscore': ['podkreślenie', 'podkreślnik'],
            'at': ['małpa', 'at'],
            'hyphen': ['łącznik', 'myślnik'],
            'dash': ['kreska', 'pauza']
        }
    },

    'sv': {  # Sueco
        'pattern': r'[åäöÅÄÖ]',
        'keywords': ['punkt', 'understreck', 'snabel-a', 'bindestreck'],
        'common_domains': ['se', 'stockholm', 'goteborg'],
        'email_terms': {
            'dot': ['punkt', 'prick'],
            'underscore': ['understreck', 'understrykning'],
            'at': ['snabel-a', 'at-tecken'],
            'hyphen': ['bindestreck', 'streck'],
            'dash': ['tankstreck', 'streck']
        }
    },

    'no': {  # Noruego
        'pattern': r'[æøåÆØÅ]',
        'keywords': ['punktum', 'understrek', 'krøllalfa', 'bindestrek'],
        'common_domains': ['no', 'oslo', 'bergen'],
        'email_terms': {
            'dot': ['punktum', 'punkt'],
            'underscore': ['understrek', 'understreking'],
            'at': ['krøllalfa', 'at-tegn'],
            'hyphen': ['bindestrek', 'strek'],
            'dash': ['tankestrek', 'strek']
        }
    },

    'fi': {  # Finlandés
        'pattern': r'[äöÄÖ]',
        'keywords': ['piste', 'alaviiva', 'kissanhäntä', 'yhdysviiva'],
        'common_domains': ['fi', 'helsinki', 'tampere'],
        'email_terms': {
            'dot': ['piste', 'piste'],
            'underscore': ['alaviiva', 'alapiirto'],
            'at': ['kissanhäntä', 'at-merkki'],
            'hyphen': ['yhdysviiva', 'viiva'],
            'dash': ['ajatusviiva', 'viiva']
        }
    },
    
    'da': {  # Danés
        'pattern': r'[æøåÆØÅ]',
        'keywords': ['punktum', 'understregning', 'snabel-a', 'bindestreg'],
        'common_domains': ['dk', 'copenhagen', 'aarhus'],
        'email_terms': {
            'dot': ['punktum', 'punkt'],
            'underscore': ['understregning', 'bundstreg'],
            'at': ['snabel-a', 'at-tegn'],
            'hyphen': ['bindestreg', 'streg'],
            'dash': ['tankestreg', 'streg']
        }
    },

    'el': {  # Griego
        'pattern': r'[\u0370-\u03FF]',
        'keywords': ['τελεία', 'κάτω παύλα', 'παπάκι', 'ενωτικό'],
        'common_domains': ['gr', 'athens', 'thessaloniki'],
        'email_terms': {
            'dot': ['τελεία', 'σημείο'],
            'underscore': ['κάτω παύλα', 'υπογράμμιση'],
            'at': ['παπάκι', 'στο'],
            'hyphen': ['ενωτικό', 'παύλα'],
            'dash': ['παύλα', 'διακοπή']
        }
    },

    'cs': {  # Checo
        'pattern': r'[áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]',
        'keywords': ['tečka', 'podtržítko', 'zavináč', 'pomlčka'],
        'common_domains': ['cz', 'prague', 'brno'],
        'email_terms': {
            'dot': ['tečka', 'bod'],
            'underscore': ['podtržítko', 'podčárník'],
            'at': ['zavináč', 'at'],
            'hyphen': ['spojovník', 'pomlčka'],
            'dash': ['pomlčka', 'čárka']
        }
    },

    'hu': {  # Húngaro
        'pattern': r'[áéíóöőúüűÁÉÍÓÖŐÚÜŰ]',
        'keywords': ['pont', 'aláhúzás', 'kukac', 'kötőjel'],
        'common_domains': ['hu', 'budapest', 'debrecen'],
        'email_terms': {
            'dot': ['pont', 'időpont'],
            'underscore': ['aláhúzás', 'alsó_vonal'],
            'at': ['kukac', 'at'],
            'hyphen': ['kötőjel', 'elválasztójel'],
            'dash': ['gondolatjel', 'vonal']
        }
    },

    'tr': {  # Turco
        'pattern': r'[çğıöşüÇĞİÖŞÜ]',
        'keywords': ['nokta', 'alt çizgi', 'et', 'tire'],
        'common_domains': ['tr', 'istanbul', 'ankara'],
        'email_terms': {
            'dot': ['nokta', 'punkt'],
            'underscore': ['alt çizgi', 'alt tire'],
            'at': ['et işareti', 'at'],
            'hyphen': ['tire', 'çizgi'],
            'dash': ['uzun çizgi', 'tire']
        }
    },
    
    'hi': {  # Hindi
        'pattern': r'[\u0900-\u097F]',
        'keywords': ['बिंदु', 'अंडरस्कोर', 'एट', 'हाइफ़न'],
        'common_domains': ['in', 'bharat', 'india'],
        'email_terms': {
            'dot': ['बिंदु', 'डॉट'],
            'underscore': ['अंडरस्कोर', 'रेखांकन'],
            'at': ['एट', 'अॅट'],
            'hyphen': ['हाइफ़न', 'योजक चिह्न'],
            'dash': ['डैश', 'विराम']
        }
    },

    'th': {  # Thai
        'pattern': r'[\u0E00-\u0E7F]',
        'keywords': ['จุด', 'ขีดล่าง', 'แอท', 'ยัติภังค์'],
        'common_domains': ['th', 'bangkok', 'thai'],
        'email_terms': {
            'dot': ['จุด', 'ดอท'],
            'underscore': ['ขีดล่าง', 'ขีดเส้นใต้'],
            'at': ['แอท', '@'],
            'hyphen': ['ยัติภังค์', 'เครื่องหมายยัติภังค์'],
            'dash': ['ขีดกลาง', 'เส้นประ']
        }
    },

    'vi': {  # Vietnamita
        'pattern': r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]',
        'keywords': ['chấm', 'gạch dưới', 'a còng', 'gạch nối'],
        'common_domains': ['vn', 'hanoi', 'saigon'],
        'email_terms': {
            'dot': ['chấm', 'dấu chấm'],
            'underscore': ['gạch dưới', 'gạch dưới'],
            'at': ['a còng', '@'],
            'hyphen': ['gạch nối', 'dấu gạch nối'],
            'dash': ['gạch ngang', 'vạch']
        }
    },

    'id': {  # Indonesio
        'pattern': r'[āīūēōĀĪŪĒŌ]',
        'keywords': ['titik', 'garis bawah', 'at', 'tanda hubung'],
        'common_domains': ['id', 'jakarta', 'indonesia'],
        'email_terms': {
            'dot': ['titik', 'dot'],
            'underscore': ['garis bawah', 'underscore'],
            'at': ['at', 'pada'],
            'hyphen': ['tanda hubung', 'strip'],
            'dash': ['garis', 'setrip']
        }
    },

    'ms': {  # Malayo
        'pattern': r'[āīūēōĀĪŪĒŌ]',
        'keywords': ['titik', 'garis bawah', 'di', 'sempang'],
        'common_domains': ['my', 'malaysia', 'kuala'],
        'email_terms': {
            'dot': ['titik', 'noktah'],
            'underscore': ['garis bawah', 'underscore'],
            'at': ['di', 'at'],
            'hyphen': ['sempang', 'tanda sambung'],
            'dash': ['sengkang', 'garis']
        }
    },

    'tl': {  # Filipino/Tagalo
        'pattern': r'[ñÑ]',
        'keywords': ['tuldok', 'salungguhit', 'at', 'gitling'],
        'common_domains': ['ph', 'manila', 'philippines'],
        'email_terms': {
            'dot': ['tuldok', 'punto'],
            'underscore': ['salungguhit', 'underscore'],
            'at': ['at', 'sa'],
            'hyphen': ['gitling', 'gatlang'],
            'dash': ['guhit', 'dash']
        }
    },

    'ar': {  # Árabe
        'pattern': r'[\u0600-\u06FF]',
        'keywords': ['نقطة', 'شرطة_سفلية', 'علامة_الات', 'واصلة'],
        'common_domains': ['sa', 'ae', 'eg'],
        'email_terms': {
            'dot': ['نقطة', 'دوت'],
            'underscore': ['شرطة_سفلية', 'خط_سفلي'],
            'at': ['علامة_الات', '@'],
            'hyphen': ['واصلة', 'شرطة'],
            'dash': ['شرطة', 'خط']
        }
    },
    
    'he': {  # Hebreo
        'pattern': r'[\u0590-\u05FF]',
        'keywords': ['נקודה', 'קו_תחתון', 'שטרודל', 'מקף'],
        'common_domains': ['il', 'israel', 'jerusalem'],
        'email_terms': {
            'dot': ['נקודה', 'דוט'],
            'underscore': ['קו_תחתון', 'קו_תחתי'],
            'at': ['שטרודל', 'כרוכית'],
            'hyphen': ['מקף', 'קו_מחבר'],
            'dash': ['קו_מפריד', 'מקף']
        }
    },

    'fa': {  # Persa/Farsi
        'pattern': r'[\u0600-\u06FF]',
        'keywords': ['نقطه', 'خط_زیر', 'اَت', 'خط_تیره'],
        'common_domains': ['ir', 'iran', 'tehran'],
        'email_terms': {
            'dot': ['نقطه', 'دات'],
            'underscore': ['خط_زیر', 'زیرخط'],
            'at': ['اَت', '@'],
            'hyphen': ['خط_تیره', 'هایفن'],
            'dash': ['خط_فاصله', 'تیره']
        }
    },

    'uk': {  # Ucraniano
        'pattern': r'[їєіґЇЄІҐ]',
        'keywords': ['крапка', 'підкреслення', 'равлик', 'дефіс'],
        'common_domains': ['ua', 'kiev', 'ukraine'],
        'email_terms': {
            'dot': ['крапка', 'точка'],
            'underscore': ['підкреслення', 'нижнє_підкреслення'],
            'at': ['равлик', 'ет'],
            'hyphen': ['дефіс', 'риска'],
            'dash': ['тире', 'довге_тире']
        }
    },

    'ro': {  # Rumano
        'pattern': r'[ăâîșțĂÂÎȘȚ]',
        'keywords': ['punct', 'liniuță_jos', 'arond', 'cratimă'],
        'common_domains': ['ro', 'romania', 'bucharest'],
        'email_terms': {
            'dot': ['punct', 'punto'],
            'underscore': ['liniuță_jos', 'subliniere'],
            'at': ['arond', 'la'],
            'hyphen': ['cratimă', 'liniuță'],
            'dash': ['linie', 'liniuță_de_pauză']
        }
    },

    'bg': {  # Búlgaro
        'pattern': r'[а-яА-Я]',
        'keywords': ['точка', 'долна_черта', 'кльомба', 'тире'],
        'common_domains': ['bg', 'bulgaria', 'sofia'],
        'email_terms': {
            'dot': ['точка', 'точка'],
            'underscore': ['долна_черта', 'подчертаване'],
            'at': ['кльомба', 'ет'],
            'hyphen': ['тире', 'дефис'],
            'dash': ['тире', 'дълго_тире']
        }
    },

    'hr': {  # Croata
        'pattern': r'[čćđšžČĆĐŠŽ]',
        'keywords': ['točka', 'podvlaka', 'at', 'spojnica'],
        'common_domains': ['hr', 'croatia', 'zagreb'],
        'email_terms': {
            'dot': ['točka', 'točka'],
            'underscore': ['podvlaka', 'donja_crta'],
            'at': ['at', 'pri'],
            'hyphen': ['spojnica', 'crtica'],
            'dash': ['crta', 'duga_crta']
        }
    },

    'sk': {  # Eslovaco
        'pattern': r'[áäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ]',
        'keywords': ['bodka', 'podčiarknutie', 'zavináč', 'spojovník'],
        'common_domains': ['sk', 'slovakia', 'bratislava'],
        'email_terms': {
            'dot': ['bodka', 'bod'],
            'underscore': ['podčiarknutie', 'podčiarknik'],
            'at': ['zavináč', 'at'],
            'hyphen': ['spojovník', 'pomlčka'],
            'dash': ['pomlčka', 'dlhá_pomlčka']
        }
    },

    'sl': {  # Esloveno
        'pattern': r'[čšžČŠŽ]',
        'keywords': ['pika', 'podčrtaj', 'afna', 'vezaj'],
        'common_domains': ['si', 'slovenia', 'ljubljana'],
        'email_terms': {
            'dot': ['pika', 'točka'],
            'underscore': ['podčrtaj', 'podčrtaj'],
            'at': ['afna', 'pri'],
            'hyphen': ['vezaj', 'črtica'],
            'dash': ['pomišljaj', 'črta']
        }
    }
}
# Nueva configuración de TLDs internacionales
INTERNATIONAL_TLDS = {
    'us': ['com', 'org', 'net', 'edu', 'gov', 'mil'],
    'uk': ['co.uk', 'org.uk', 'me.uk', 'ac.uk', 'gov.uk'],
    'eu': ['eu', 'de', 'fr', 'es', 'it', 'nl', 'be', 'at', 'dk', 'fi', 'gr', 'ie', 'pt', 'se'],
    'asia': ['jp', 'cn', 'kr', 'in', 'sg', 'hk', 'tw', 'my', 'th', 'vn'],
    'ru': ['ru', 'su', 'рф', 'moscow', 'спб'],
    # Nuevos TLDs regionales
    'pl': ['pl', 'com.pl', 'net.pl', 'org.pl'],
    'cz': ['cz', 'com.cz', 'net.cz'],
    'hr': ['hr', 'com.hr'],
    'hu': ['hu', 'co.hu'],
    'sk': ['sk', 'com.sk'],
    'si': ['si', 'com.si'],
    'bg': ['bg', 'com.bg'],
    'ro': ['ro', 'com.ro'],
    'ua': ['ua', 'com.ua'],
    'th': ['th', 'co.th', 'ac.th'],
    'vn': ['vn', 'com.vn'],
    'id': ['id', 'co.id'],
    'my': ['my', 'com.my'],
    'ph': ['ph', 'com.ph']
}

# Configuraciones adicionales para los nuevos idiomas
NEW_LANGUAGE_SETTINGS = {
    'default_tlds': {
        'nl': ['nl', 'amsterdam', 'rotterdam'],
        'pl': ['pl', 'warsaw', 'krakow'],
        'sv': ['se', 'stockholm', 'gothenburg'],
        'no': ['no', 'oslo', 'bergen'],
        'fi': ['fi', 'helsinki', 'tampere'],
        'da': ['dk', 'copenhagen', 'aarhus'],
        'el': ['gr', 'athens', 'thessaloniki'],
        'cs': ['cz', 'prague', 'brno'],
        'hu': ['hu', 'budapest', 'debrecen'],
        'tr': ['tr', 'istanbul', 'ankara'],
        'hi': ['in', 'india', 'bharat'],
        'th': ['th', 'bangkok', 'thai'],
        'vi': ['vn', 'vietnam', 'hanoi'],
        'id': ['id', 'indonesia', 'jakarta'],
        'ms': ['my', 'malaysia', 'kuala'],
        'tl': ['ph', 'philippines', 'manila'],
        'ar': ['sa', 'ae', 'eg'],
        'he': ['il', 'israel', 'jerusalem'],
        'fa': ['ir', 'iran', 'tehran'],
        'uk': ['ua', 'ukraine', 'kiev'],
        'ro': ['ro', 'romania', 'bucharest'],
        'bg': ['bg', 'bulgaria', 'sofia'],
        'hr': ['hr', 'croatia', 'zagreb'],
        'sk': ['sk', 'slovakia', 'bratislava'],
        'sl': ['si', 'slovenia', 'ljubljana']
    },
    
    'script_direction': {
        'ar': 'rtl',
        'he': 'rtl',
        'fa': 'rtl'
    }
}