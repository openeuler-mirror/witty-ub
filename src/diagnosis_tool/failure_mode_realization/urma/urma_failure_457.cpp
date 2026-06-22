#include "urma_failure_457.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure457> g_urma("urma_457");

bool UrmaFailure457::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfc") != std::string::npos &&
           message.find("jfc cfg depth of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos;
}

std::string UrmaFailure457::GetName() const
{
    return "JFC配置值超过设备能力导致分配JFC失败";
}

std::string UrmaFailure457::GetRootCauseDesc() const
{
    return "urma_alloc_jfc会按设备能力校验JFC配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure457::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure457::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure457::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfc，jfc cfg depth of range, depth:，, max_depth:。";
}

std::string UrmaFailure457::GetId() const
{
    return "urma_457";
}
} // namespace diag
