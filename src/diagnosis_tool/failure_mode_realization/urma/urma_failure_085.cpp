#include "urma_failure_085.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure085> g_urma("urma_085");

bool UrmaFailure085::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'RM jetty import requires drv_ext.vjetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure085::GetName() const
{
    return "Jetty导入时下层资源准备失败";
}

std::string UrmaFailure085::GetRootCauseDesc() const
{
    return "函数负责导入Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure085::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure085::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure085::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_pjetty，RM jetty import requires drv_ext.vjetty.。";
}

std::string UrmaFailure085::GetId() const
{
    return "urma_085";
}

} // namespace diag
