#include "urma_failure_637.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure637> g_urma("urma_637");

bool UrmaFailure637::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure637::GetName() const
{
    return "URMA context无效导致释放JFC失败";
}

std::string UrmaFailure637::GetRootCauseDesc() const
{
    return "函数用于释放JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure637::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure637::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure637::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_free_jfc，Invalid parameter";
}

std::string UrmaFailure637::GetId() const
{
    return "urma_637";
}

} // namespace diag
