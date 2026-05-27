#include "urma_failure_331.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure331> g_urma("urma_331");

bool UrmaFailure331::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pjfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create pjfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure331::GetName() const
{
    return "物理 JFS创建时下层资源准备失败";
}

std::string UrmaFailure331::GetRootCauseDesc() const
{
    return "函数负责创建物理 JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure331::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure331::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure331::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfs，Failed to create pjfs。";
}

std::string UrmaFailure331::GetId() const
{
    return "urma_331";
}

} // namespace diag
