#include "urma_failure_650.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure650> g_urma("urma_650");

bool UrmaFailure650::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter,' | grep -F 'jfc in the array is NULL.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure650::GetName() const
{
    return "删除JFC所需输入对象无效导致删除JFC失败";
}

std::string UrmaFailure650::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的删除JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure650::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure650::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure650::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfc_batch，Invalid parameter,，jfc in the array is NULL.";
}

std::string UrmaFailure650::GetId() const
{
    return "urma_650";
}

} // namespace diag
