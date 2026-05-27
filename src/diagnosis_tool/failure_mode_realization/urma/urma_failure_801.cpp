#include "urma_failure_801.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure801> g_urma("urma_801");

bool UrmaFailure801::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure801::GetName() const
{
    return "JFS对象无效导致激活JFS失败";
}

std::string UrmaFailure801::GetRootCauseDesc() const
{
    return "函数用于激活JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure801::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure801::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure801::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure801::GetId() const
{
    return "urma_801";
}

} // namespace diag
