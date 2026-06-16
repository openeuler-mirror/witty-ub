#include "urma_failure_873.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure873> g_urma("urma_873");

bool UrmaFailure873::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid option value.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure873::GetName() const
{
    return "URMA context、设备对象、provider操作表无效导致设置context失败";
}

std::string UrmaFailure873::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA "
           "context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure873::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure873::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure873::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_context_opt，Invalid option value.。";
}

std::string UrmaFailure873::GetId() const
{
    return "urma_873";
}

} // namespace diag
