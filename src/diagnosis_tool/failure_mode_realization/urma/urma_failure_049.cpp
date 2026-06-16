#include "urma_failure_049.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure049> g_urma("urma_049");

bool UrmaFailure049::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_uninit' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure049::GetName() const
{
    return "执行URMA资源所需输入对象无效导致释放设备失败";
}

std::string UrmaFailure049::GetRootCauseDesc() const
{
    return "函数用于释放设备，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure049::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure049::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure049::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_uninit，Invalid parameter.。";
}

std::string UrmaFailure049::GetId() const
{
    return "urma_049";
}

} // namespace diag
