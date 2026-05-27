#include "urma_failure_673.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure673> g_urma("urma_673");

bool UrmaFailure673::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, index:' | grep -F 'jfr in the array is NULL.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure673::GetName() const
{
    return "JFR对象无效导致删除JFR失败";
}

std::string UrmaFailure673::GetRootCauseDesc() const
{
    return "函数用于删除JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure673::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure673::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure673::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfr_batch，Invalid parameter, index:，jfr in the array is NULL.";
}

std::string UrmaFailure673::GetId() const
{
    return "urma_673";
}

} // namespace diag
