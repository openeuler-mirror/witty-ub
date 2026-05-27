#include "urma_failure_793.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure793> g_urma("urma_793");

bool UrmaFailure793::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:' | grep -F ', order_type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure793::GetName() const
{
    return "JFS对象无效导致激活JFS失败";
}

std::string UrmaFailure793::GetRootCauseDesc() const
{
    return "函数用于激活JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure793::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure793::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure793::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfs，Invalid parameter, trans_mode:，, order_type:";
}

std::string UrmaFailure793::GetId() const
{
    return "urma_793";
}

} // namespace diag
