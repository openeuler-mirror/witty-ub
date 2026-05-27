#include "urma_failure_740.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure740> g_urma("urma_740");

bool UrmaFailure740::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure740::GetName() const
{
    return "URMA context、JFS对象无效导致去激活JFS失败";
}

std::string UrmaFailure740::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure740::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure740::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure740::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_deactive_jfs，Invalid parameter";
}

std::string UrmaFailure740::GetId() const
{
    return "urma_740";
}

} // namespace diag
