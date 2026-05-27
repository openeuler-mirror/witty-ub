#include "urma_failure_591.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure591> g_urma("urma_591");

bool UrmaFailure591::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_config_perf_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Urma perf config failed. perf_attr is invalid.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure591::GetName() const
{
    return "执行URMA资源所需输入对象无效导致执行URMA资源失败";
}

std::string UrmaFailure591::GetRootCauseDesc() const
{
    return "函数用于执行URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure591::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure591::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure591::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_config_perf_attr，Urma perf config failed. perf_attr is invalid.。";
}

std::string UrmaFailure591::GetId() const
{
    return "urma_591";
}

} // namespace diag
