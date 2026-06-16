#include "urma_failure_093.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure093> g_urma("urma_093");

bool UrmaFailure093::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to import vjetty, []:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure093::GetName() const
{
    return "虚拟 Jetty导入时下层资源准备失败";
}

std::string UrmaFailure093::GetRootCauseDesc() const
{
    return "函数负责导入虚拟 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure093::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure093::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure093::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_pjfr，Failed to import vjetty, []:。";
}

std::string UrmaFailure093::GetId() const
{
    return "urma_093";
}

} // namespace diag
