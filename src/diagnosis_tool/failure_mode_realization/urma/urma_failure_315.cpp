#include "urma_failure_315.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure315> g_urma("urma_315");

bool UrmaFailure315::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_seg") != std::string::npos &&
           message.find("Failed to alloc bondp segment comp") != std::string::npos;
}

std::string UrmaFailure315::GetName() const
{
    return "bondpseg分配失败导致注册Segment失败";
}

std::string UrmaFailure315::GetRootCauseDesc() const
{
    return "bondp_register_seg执行注册Segment前需要准备bondpseg，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure315::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure315::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure315::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_seg，Failed to alloc bondp segment comp。";
}

std::string UrmaFailure315::GetId() const
{
    return "urma_315";
}
} // namespace diag
