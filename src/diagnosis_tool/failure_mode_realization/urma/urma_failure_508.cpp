#include "urma_failure_508.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure508> g_urma("urma_508");

bool UrmaFailure508::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'RM jfr import requires drv_ext.vjfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure508::GetName() const
{
    return "JFR导入时下层资源准备失败";
}

std::string UrmaFailure508::GetRootCauseDesc() const
{
    return "函数负责导入JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure508::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure508::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure508::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_pjfr，RM jfr import requires drv_ext.vjfs。";
}

std::string UrmaFailure508::GetId() const
{
    return "urma_508";
}

} // namespace diag
