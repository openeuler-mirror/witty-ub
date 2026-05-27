#include "urma_failure_059.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure059> g_urma("urma_059");

bool UrmaFailure059::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to create jfs datapath ctx'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure059::GetName() const
{
    return "JFS创建时下层资源准备失败";
}

std::string UrmaFailure059::GetRootCauseDesc() const
{
    return "函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure059::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure059::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure059::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jfs_p_vjetty_info，Failed to create jfs datapath ctx。";
}

std::string UrmaFailure059::GetId() const
{
    return "urma_059";
}

} // namespace diag
