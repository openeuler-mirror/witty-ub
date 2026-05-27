#include "urma_failure_861.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure861> g_urma("urma_861");

bool UrmaFailure861::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_rearm_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure861::GetName() const
{
    return "执行JFC所需输入对象无效导致轮询JFC失败";
}

std::string UrmaFailure861::GetRootCauseDesc() const
{
    return "函数用于轮询JFC，调用方传入的执行JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure861::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure861::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure861::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_rearm_jfc，Invalid parameter.。";
}

std::string UrmaFailure861::GetId() const
{
    return "urma_861";
}

} // namespace diag
