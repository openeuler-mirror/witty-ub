#include "urma_failure_298.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure298> g_urma("urma_298");

bool UrmaFailure298::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_unregister_health_check_seg_for_jetty") != std::string::npos &&
           message.find("Failed to unregister health check segment") != std::string::npos;
}

std::string UrmaFailure298::GetName() const
{
    return "下层注册或导入返回失败导致注销health、Segment、FOR失败";
}

std::string UrmaFailure298::GetRootCauseDesc() const
{
    return "bondp_unregister_health_check_seg_for_"
           "jetty在注销health、Segment、FOR时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure298::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure298::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure298::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unregister_health_check_seg_for_jetty，Failed to unregister "
           "health check"
           " segment。";
}

std::string UrmaFailure298::GetId() const
{
    return "urma_298";
}
} // namespace diag
