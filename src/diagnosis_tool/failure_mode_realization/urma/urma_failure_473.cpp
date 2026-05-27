#include "urma_failure_473.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure473> g_urma("urma_473");

bool UrmaFailure473::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_dmac' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure473::GetName() const
{
    return "URMA context、provider操作表无效导致获取context失败";
}

std::string UrmaFailure473::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure473::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure473::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure473::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_dmac，Invalid parameter.。";
}

std::string UrmaFailure473::GetId() const
{
    return "urma_473";
}

} // namespace diag
