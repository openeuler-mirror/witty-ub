#include "urma_failure_658.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure658> g_urma("urma_658");

bool UrmaFailure658::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure658::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供delete_jfs操作实现无效导致删除JFS失败";
}

std::string UrmaFailure658::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供delete_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure658::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure658::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure658::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfs，Invalid parameter.";
}

std::string UrmaFailure658::GetId() const
{
    return "urma_658";
}

} // namespace diag
