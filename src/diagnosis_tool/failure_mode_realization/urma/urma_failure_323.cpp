#include "urma_failure_323.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure323> g_urma("urma_323");

bool UrmaFailure323::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pjfce' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Fail to add fd:' | grep -F 'to epoll fd:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure323::GetName() const
{
    return "文件描述符数据通路处理失败";
}

std::string UrmaFailure323::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure323::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure323::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure323::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfce，Fail to add fd:，to epoll fd:。";
}

std::string UrmaFailure323::GetId() const
{
    return "urma_323";
}

} // namespace diag
