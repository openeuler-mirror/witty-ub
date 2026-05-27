#include "urma_failure_573.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure573> g_urma("urma_573");

bool UrmaFailure573::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfr state is wrong in deactive_jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure573::GetName() const
{
    return "JFR数据通路处理失败";
}

std::string UrmaFailure573::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure573::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure573::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure573::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfr，jfr state is wrong in deactive_jfr.";
}

std::string UrmaFailure573::GetId() const
{
    return "urma_573";
}

} // namespace diag
