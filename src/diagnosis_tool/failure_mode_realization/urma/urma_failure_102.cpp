#include "urma_failure_102.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure102> g_urma("urma_102");

bool UrmaFailure102::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_register_health_check_seg_for_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc health check buffer'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure102::GetName() const
{
    return "健康检查相关临时结构或命令参数分配失败";
}

std::string UrmaFailure102::GetRootCauseDesc() const
{
    return "函数在分配健康检查前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure102::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure102::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure102::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_register_health_check_seg_for_jetty，Failed to alloc health check buffer";
}

std::string UrmaFailure102::GetId() const
{
    return "urma_102";
}

} // namespace diag
