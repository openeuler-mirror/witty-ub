#include "urma_failure_337.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure337> g_urma("urma_337");

bool UrmaFailure337::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_start_health_check_thread' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to create health epoll'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure337::GetName() const
{
    return "健康检查创建时下层资源准备失败";
}

std::string UrmaFailure337::GetRootCauseDesc() const
{
    return "函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure337::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure337::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure337::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_start_health_check_thread，Failed to create health epoll。";
}

std::string UrmaFailure337::GetId() const
{
    return "urma_337";
}

} // namespace diag
