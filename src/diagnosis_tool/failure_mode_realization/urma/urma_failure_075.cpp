#include "urma_failure_075.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure075> g_urma("urma_075");

bool UrmaFailure075::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to create vjetty,'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure075::GetName() const
{
    return "虚拟 Jetty创建时下层资源准备失败";
}

std::string UrmaFailure075::GetRootCauseDesc() const
{
    return "函数负责创建虚拟 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure075::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure075::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure075::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，Failed to create vjetty,。";
}

std::string UrmaFailure075::GetId() const
{
    return "urma_075";
}

} // namespace diag
