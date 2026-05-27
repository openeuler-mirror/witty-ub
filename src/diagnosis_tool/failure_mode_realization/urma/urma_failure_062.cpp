#include "urma_failure_062.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure062> g_urma("urma_062");

bool UrmaFailure062::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfr_p_vjetty_info' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to create pjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure062::GetName() const
{
    return "物理 JFR创建时下层资源准备失败";
}

std::string UrmaFailure062::GetRootCauseDesc() const
{
    return "函数负责创建物理 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure062::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure062::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure062::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jfr_p_vjetty_info，Failed to create pjfr。";
}

std::string UrmaFailure062::GetId() const
{
    return "urma_062";
}

} // namespace diag
