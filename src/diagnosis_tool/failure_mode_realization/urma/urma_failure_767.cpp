#include "urma_failure_767.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure767> g_urma("urma_767");

bool UrmaFailure767::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure767::GetName() const
{
    return "provider操作表无效导致设置JFC失败";
}

std::string UrmaFailure767::GetRootCauseDesc() const
{
    return "函数用于设置JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure767::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure767::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure767::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfc_opt，invalid opt id or opt len";
}

std::string UrmaFailure767::GetId() const
{
    return "urma_767";
}

} // namespace diag
