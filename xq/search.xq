
    let $matches := for $hit in $hits 
        let $expanded :=  kwic:expand($hit)
        return 
            for $m in $expanded//exist:match
            return ($m, util:collection-name($hit), util:document-name($hit), $expanded)
    let $hitCount :=  count($matches)
    
    let $results := for $match in subsequence($matches, $a_start, $a_limit)
        let $matchNode := $match[1]
        let $path := fn:concat($match[2], "/", $match[3])
        let $docname := collection("/db/repository/inventory")//ti:online[@docname=$path]
        let $editionNode := $docname/..
        
        let $urn := if ($editionNode/@urn)
            then fn:string($editionNode/@urn)
        else
            let $edition := tokenize($docname/../@projid, ":")[2]
            let $work := tokenize($docname/../../@projid, ":")[2]
            let $textgroup := tokenize($docname/../../../@projid, ":")[2]
            
            return concat("urn:cts:",$textgroup,".",$work,".",$edition)
            
        let $expanded := $match[4]
        
        let $xpath := replace(ahabx:smallestCitationNode($docname/..), "//", "/   /")
        let $tokenizedPath := tokenize($xpath, "/")
        
        let $indexOfBody := if(index-of($tokenizedPath, "tei:body"))
            then index-of($tokenizedPath, "tei:body")
            else index-of($tokenizedPath, "body")
        
        let $subsequence := subsequence($tokenizedPath, $indexOfBody + 1, count($tokenizedPath) - $indexOfBody)
        let $joinedXpath := fn:string-join($subsequence, "/")
        let $reduced_xpath := replace($joinedXpath, "   ", "")
        let $lastChar := substring($reduced_xpath, string-length($reduced_xpath), 1)
        let $eval := if($lastChar = "]")
        then fn:concat("$expanded/", substring($reduced_xpath, 1, string-length($reduced_xpath) - 1), " and ./descendant::node() is $matchNode]")
        else fn:concat("$expanded/", $reduced_xpath, "[.//node() = $matchNode]") 
        let $contexts := util:eval($eval)
        
        return for $context in $contexts
            let $passage := for $citation in $docname//ti:citation
                let $label := fn:lower-case(fn:string($citation/@label))
                return if (fn:string($citation/@xpath) = "//tei:l[@n='?']" or fn:string($citation/@xpath) = "/tei:l[@n='?']") (: Dirty hack :)
                then fn:string($context/ancestor-or-self::node()[@n][1]/@n)
                else fn:string($context/ancestor-or-self::node()[@n and fn:lower-case(@type)=$label][1]/@n)
                
            let $passage_urn := fn:concat($urn, ":", fn:string-join($passage, "."))
            
            return for $context_match in $context//exist:match
                return 
                    element ahab:result {
                        element ahab:urn { $urn },
                        element ahab:passageUrn { $passage_urn },
                        element ahab:text { kwic:get-summary($context, $context_match, $config) }
                    }
    return 
        element ahab:reply {
            element ahab:query   { $a_query },
            element ahab:urn     { $a_urn },
            element ahab:results { 
                attribute ahab:start { $a_start },
                attribute ahab:limit { $a_limit },
                attribute ahab:count { $hitCount },
                $results
            }
        }