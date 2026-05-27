#include "urma_failure_500.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure500> g_urma("urma_500");

bool UrmaFailure500::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_perf_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Urma perf info get failed, perf_buf or length is invalid'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure500::GetName() const
{
    return "获取URMA资源所需输入对象无效导致获取锁失败";
}

std::string UrmaFailure500::GetRootCauseDesc() const
{
    return "函数用于获取锁，调用方传入的获取URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure500::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure500::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure500::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_perf_info，Urma perf info get failed, perf_buf or length is invalid";
}

std::string UrmaFailure500::GetId() const
{
    return "urma_500";
}

} // namespace diag
