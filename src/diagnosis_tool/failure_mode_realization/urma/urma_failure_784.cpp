#include "urma_failure_784.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure784> g_urma("urma_784");

bool UrmaFailure784::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure784::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供modify_jfs操作实现无效导致修改JFS失败";
}

std::string UrmaFailure784::GetRootCauseDesc() const
{
    return "函数用于修改JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供modify_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure784::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure784::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure784::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_modify_jfs，Invalid parameter.";
}

std::string UrmaFailure784::GetId() const
{
    return "urma_784";
}

} // namespace diag
