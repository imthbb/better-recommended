page = document.querySelector('.videos')

exampleVid = document.querySelector('.videos li')

vidsPerRow = Math.floor((screen.width - 130) / 196)
vidPerColumn = Math.floor(screen.height / 223)
pageVidsAmount = vidsPerRow * vidPerColumn


pageNumber = document.querySelector('.page-number')
pageName  = document.querySelector('.page-name')
changeVidTypes = document.querySelector('.sidebar-section input')


function vidData(video){
    newVid = exampleVid.cloneNode(true)

    url = newVid.querySelector('a')
    url.setAttribute('href', video['url'])

    thumbnail = newVid.querySelector('.thumbnail')
    thumbnail.setAttribute('src', video['thumbnail'])

    if('frmt_duration' in video){
        newVid.querySelector('.duration').innerText = video['frmt_duration']
    }
    else{
        newVid.querySelector('.duration-bubble').style.cssText = `opacity:0;`
    }

    title = newVid.querySelector('.title')
    unescapedTitleText = new DOMParser().parseFromString(video['title'],'text/html')
        .querySelector('html').textContent
    title.innerText = unescapedTitleText

    channel = newVid.querySelector('.channel')
    unescapedChannelText = new DOMParser().parseFromString(video['name'],'text/html')
        .querySelector('html').textContent
    channel.innerText = unescapedChannelText
    channel.setAttribute('href', video['channel_url'])

    if(video['url'].includes('twitch.tv')){
        icon = newVid.querySelector('.icon')
        icon.setAttribute('src', 'tw.ico')
        icon.style.cssText = `margin-top:0px;margin-left:5px;margin-right:1px;`
    }
    else if(video['url'].includes('bitchute.com')){
        icon = newVid.querySelector('.icon')
        icon.setAttribute('src', 'bt.webp')
        icon.style.cssText = `margin-left:5px;margin-top:-1px;`
    }

    if('frmt_date' in video){
        newVid.querySelector('.date').innerText = video['frmt_date']
    }

    if('frmt_views' in video){
        newVid.querySelector('.views').innerText = video['frmt_views']
    }

    return newVid
}


function durationWidth(){
    document.querySelectorAll('.duration-bubble').forEach(i => {
        durLen = i.querySelector('.duration').textContent.length
        switch(durLen){
            case 4:
                i.style.cssText=`width:30px;`
                break
            case 5:
                i.style.cssText=`width:36px;`
                break
            case 7:
                i.style.cssText=`width:47px;`
                break
            }
    })
}


function newPage(){
    from = pageVidsAmount * (currentPage - 1)
    to = pageVidsAmount * currentPage

    document.querySelectorAll('.videos li').forEach(i => {
        i.remove()
    })

    for(i = from; i < to; i++){
        if(i < vids.length){
            page.append(vidData(vids[i]))
        }
    }

    pageNumber.innerText = `${currentPage}/${pages}`

    durationWidth()
}


window.onwheel = function(event){
    if(event.deltaY > 0){ // down
        if(currentPage < pages){
        currentPage++
        newPage()
        }
    }
    else{ // up
        if(currentPage != 1){
            currentPage--
            newPage()
        }
    }
}


function videoType(){
    if(changeVidTypes.checked){
        vids = recVideos
        pageName.innerText = 'recommendations'
    }
    else{
        vids = subVideos
        pageName.innerText = 'subscriptions'
    }

    pages = Math.ceil(vids.length / pageVidsAmount)
    currentPage = 1
    newPage()
}


changeVidTypes.addEventListener('change', function(){
    videoType()
})

videoType()
