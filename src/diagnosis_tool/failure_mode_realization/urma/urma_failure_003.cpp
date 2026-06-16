#include "urma_failure_003.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure003> g_urma("urma_003");

bool UrmaFailure003::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'init_active_indices' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid active port id, value: 0x' | grep -F 'x.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure003::GetName() const
{
    return "初始化URMA资源所需输入对象无效导致激活端口失败";
}

std::string UrmaFailure003::GetRootCauseDesc() const
{
    return "函数用于激活端口，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure003::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure003::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：init_active_indices，Invalid active port id, value: 0x，x.。";
}

std::string UrmaFailure003::GetId() const
{
    return "urma_003";
}

} // namespace diag
