#include "urma_failure_103.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure103> g_urma("urma_103");

bool UrmaFailure103::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_register_health_check_seg_for_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to register health check segment'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure103::GetName() const
{
    return "健康检查注册时下层资源准备失败";
}

std::string UrmaFailure103::GetRootCauseDesc() const
{
    return "函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure103::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure103::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure103::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_register_health_check_seg_for_jetty，Failed to register health check "
           "segment";
}

std::string UrmaFailure103::GetId() const
{
    return "urma_103";
}

} // namespace diag
