#include "urma_failure_753.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure753> g_urma("urma_753");

bool UrmaFailure753::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_drivers") != std::string::npos && message.find("strrchr") != std::string::npos &&
           message.find("failed, errno:") != std::string::npos;
}

std::string UrmaFailure753::GetName() const
{
    return "打开drivers执行失败导致打开drivers失败";
}

std::string UrmaFailure753::GetRootCauseDesc() const
{
    return "urma_open_drivers执行打开drivers时依赖的打开drivers步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure753::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure753::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure753::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_drivers，strrchr，failed, errno:。";
}

std::string UrmaFailure753::GetId() const
{
    return "urma_753";
}
} // namespace diag
