#include "urma_failure_444.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure444> g_urma("urma_444");

bool UrmaFailure444::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfc") != std::string::npos &&
           message.find("jfc cfg depth of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos;
}

std::string UrmaFailure444::GetName() const
{
    return "JFC配置值超过设备能力导致创建JFC失败";
}

std::string UrmaFailure444::GetRootCauseDesc() const
{
    return "urma_create_jfc会按设备能力校验JFC配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure444::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure444::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure444::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfc，jfc cfg depth of range, depth:，, max_depth:。";
}

std::string UrmaFailure444::GetId() const
{
    return "urma_444";
}
} // namespace diag
