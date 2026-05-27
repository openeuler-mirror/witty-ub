#include "urma_failure_865.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure865> g_urma("urma_865");

bool UrmaFailure865::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid option value len.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure865::GetName() const
{
    return "URMA context、设备对象、provider操作表无效导致设置context失败";
}

std::string UrmaFailure865::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA "
           "context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure865::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure865::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure865::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_context_opt，Invalid option value len.";
}

std::string UrmaFailure865::GetId() const
{
    return "urma_865";
}

} // namespace diag
