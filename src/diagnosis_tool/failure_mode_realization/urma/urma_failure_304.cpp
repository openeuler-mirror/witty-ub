#include "urma_failure_304.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure304> g_urma("urma_304");

bool UrmaFailure304::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_health_check_tseg") != std::string::npos &&
           message.find("Invalid rjetty for health check seg import, health check disabled") != std::string::npos;
}

std::string UrmaFailure304::GetName() const
{
    return "health、TSEG状态不满足要求导致导入health、TSEG失败";
}

std::string UrmaFailure304::GetRootCauseDesc() const
{
    return "bondp_import_health_check_"
           "tseg执行导入health、TSEG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure304::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure304::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure304::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_health_check_tseg，Invalid rjetty for health check seg "
           "import, he"
           "alth check disabled。";
}

std::string UrmaFailure304::GetId() const
{
    return "urma_304";
}
} // namespace diag
