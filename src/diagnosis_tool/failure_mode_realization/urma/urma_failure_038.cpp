#include "urma_failure_038.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure038> g_urma("urma_038");

bool UrmaFailure038::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'failed to init create jetty cmd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure038::GetName() const
{
    return "Jetty初始化时下层资源准备失败";
}

std::string UrmaFailure038::GetRootCauseDesc() const
{
    return "函数负责初始化Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure038::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure038::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure038::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jetty，failed to init create jetty cmd。";
}

std::string UrmaFailure038::GetId() const
{
    return "urma_038";
}

} // namespace diag
