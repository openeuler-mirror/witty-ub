#include "urma_failure_104.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure104> g_urma("urma_104");

bool UrmaFailure104::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_register_health_check_seg_for_jetty' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to alloc health check buffer'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure104::GetName() const
{
    return "健康检查相关临时结构或命令参数分配失败";
}

std::string UrmaFailure104::GetRootCauseDesc() const
{
    return "函数在分配健康检查前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure104::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure104::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure104::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_health_check_seg_for_jetty，Failed to alloc health check "
           "buffer。";
}

std::string UrmaFailure104::GetId() const
{
    return "urma_104";
}

} // namespace diag
