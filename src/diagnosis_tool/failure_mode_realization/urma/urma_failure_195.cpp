#include "urma_failure_195.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure195> g_urma("urma_195");

bool UrmaFailure195::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfr") != std::string::npos &&
           message.find("jfr cfg out of range, depth:") != std::string::npos &&
           message.find(", max_depth:") != std::string::npos && message.find(", sge:") != std::string::npos &&
           message.find(", max_sge:") != std::string::npos;
}

std::string UrmaFailure195::GetName() const
{
    return "JFR配置值超过设备能力导致创建JFR失败";
}

std::string UrmaFailure195::GetRootCauseDesc() const
{
    return "urma_create_jfr会按设备能力校验JFR配置，深度、数量或索引超过硬件/驱动上限时不能继续创建或修改资源。";
}

RootCause UrmaFailure195::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure195::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure195::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfr，jfr cfg out of range, depth:，, max_depth:，, sge:，, "
           "max_sge:。";
}

std::string UrmaFailure195::GetId() const
{
    return "urma_195";
}
} // namespace diag
