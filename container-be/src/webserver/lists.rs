
/// Postgres does not support unsigned int so we use i64 to represent the BIGSERIAL type which is a BIGINT in SQL
type DbBigSerial = i64;

#[derive(Deserialize, Serialize, Debug, sqlx::FromRow)]
pub struct DbId {
    id: DbBigSerial,
}

pub struct SerializeDecimal;
impl serde_with::SerializeAs<Decimal> for SerializeDecimal {
    fn serialize_as<S: Serializer>(source: &Decimal, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&source.to_string())
    }
}

impl<'de> serde_with::DeserializeAs<'de, Decimal> for SerializeDecimal {
    fn deserialize_as<D>(deserializer: D) -> Result<Decimal, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        Decimal::from_str_exact(&s).map_err(serde::de::Error::custom)
    }
}

#[derive(Serialize)]
#[serde(rename_all = "lowercase")]
enum SortOrder {
    Asc,
    Desc,
}

pub struct PageSort {
    property: String,
    direction: SortOrder,
}

// The query parameters for list_todos.
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PageOptions {
    pub page: Option<DbBigSerial>,
    pub size: Option<DbBigSerial>,
    #[serde(flatten)]
    pub sort: Option<DbBigSerial>,
}

impl Default for PageOptions {
    fn default() -> Self {
        Self {
            size: Some(5),
            page: Some(0),
            sort: None,
        }
    }
}

impl PageOptions {
    pub fn defaulting(inval: PageOptions) -> PageOptions {
        PageOptions {
            size: if inval.size.is_some() {
                inval.size
            } else {
                PageOptions::default().size
            },
            page: if inval.page.is_some() {
                inval.page
            } else {
                PageOptions::default().page
            },
            sort: if inval.sort.is_some() {
                inval.sort
            } else {
                PageOptions::default().sort
            },
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ListPages {
    ids: Vec<DbBigSerial>,
    pagination: PageOptions,
}

impl warp::Reply for ListPages {
    fn into_response(self) -> warp::reply::Response {
        warp::reply::json(&self).into_response()
    }
}
