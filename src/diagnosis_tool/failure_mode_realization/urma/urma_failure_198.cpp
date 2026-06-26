#include "urma_failure_198.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure198> g_urma("urma_198");

bool UrmaFailure198::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfr") != std::string::npos &&
           message.find("jfr cfg out of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos && message.find(", sge:") != std::string::npos &&
           message.find(", max_sge:") != std::string::npos;
}

std::string UrmaFailure198::GetName() const
{
    return "JFR配置值超过设备能力导致分配JFR失败";
}

std::string UrmaFailure198::GetRootCauseDesc() const
{
    return "urma_alloc_jfr会按设备能力校验JFR配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure198::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure198::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure198::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfr，jfr cfg out of range, depth:，, max_depth:，, sge:，, "
           "max_sge:。";
}

std::string UrmaFailure198::GetId() const
{
    return "urma_198";
}
} // namespace diag
