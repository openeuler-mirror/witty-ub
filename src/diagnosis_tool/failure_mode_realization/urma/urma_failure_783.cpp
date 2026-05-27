#include "urma_failure_783.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure783> g_urma("urma_783");

bool UrmaFailure783::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure783::GetName() const
{
    return "URMA context、设备对象、JFS对象无效导致修改JFS失败";
}

std::string UrmaFailure783::GetRootCauseDesc() const
{
    return "函数用于修改JFS，调用方传入的URMA context、设备对象、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure783::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure783::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure783::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_modify_jfs，Invalid parameter.";
}

std::string UrmaFailure783::GetId() const
{
    return "urma_783";
}

} // namespace diag
