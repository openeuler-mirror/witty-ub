#include "urma_failure_491.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure491> g_urma("urma_491");

bool UrmaFailure491::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_log_set_thread_tag' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure491::GetName() const
{
    return "设置线程所需输入对象无效导致设置线程失败";
}

std::string UrmaFailure491::GetRootCauseDesc() const
{
    return "函数用于设置线程，调用方传入的设置线程所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure491::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure491::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure491::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_log_set_thread_tag，Invalid parameter.。";
}

std::string UrmaFailure491::GetId() const
{
    return "urma_491";
}

} // namespace diag
