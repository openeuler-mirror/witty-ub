#include "urma_failure_798.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure798> g_urma("urma_798");

bool UrmaFailure798::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure798::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供deactive_jfs操作实现无效导致去激活JFS失败";
}

std::string UrmaFailure798::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供deactive_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure798::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure798::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure798::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfs，Invalid parameter.";
}

std::string UrmaFailure798::GetId() const
{
    return "urma_798";
}

} // namespace diag
