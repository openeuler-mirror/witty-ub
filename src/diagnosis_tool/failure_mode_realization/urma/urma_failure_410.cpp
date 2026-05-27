#include "urma_failure_410.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure410> g_urma("urma_410");

bool UrmaFailure410::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_register_log_func' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure410::GetName() const
{
    return "注册URMA资源所需输入对象无效导致注册URMA资源失败";
}

std::string UrmaFailure410::GetRootCauseDesc() const
{
    return "函数用于注册URMA资源，调用方传入的注册URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure410::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure410::GetFixSuggDesc() const
{
    return "当前不会触发失败";
}

std::string UrmaFailure410::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_log_func，Invalid parameter.。";
}

std::string UrmaFailure410::GetId() const
{
    return "urma_410";
}

} // namespace diag
