#include "urma_failure_074.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure074> g_urma("urma_074");

bool UrmaFailure074::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Failed to register health check seg for jetty creation'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure074::GetName() const
{
    return "健康检查注册时下层资源准备失败";
}

std::string UrmaFailure074::GetRootCauseDesc() const
{
    return "函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure074::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure074::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure074::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，Failed to register health check seg for "
           "jetty creation。";
}

std::string UrmaFailure074::GetId() const
{
    return "urma_074";
}

} // namespace diag
