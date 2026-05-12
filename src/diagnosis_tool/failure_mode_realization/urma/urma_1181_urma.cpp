#include "urma_1181_urma.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1181Urma> g_urma("urma_1181");

bool Urma1181Urma::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {
        "urma_1182", "urma_1185", "urma_1187", "urma_1189", "urma_1191", "urma_1193", "urma_1195", "urma_1197",
        "urma_1199", "urma_1202", "urma_1205", "urma_1207", "urma_1209", "urma_1211", "urma_1213", "urma_1215",
        "urma_1217", "urma_1219", "urma_1222", "urma_1225", "urma_1227", "urma_1230", "urma_1232"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1181Urma::GetName() const
{
    return "其他URMA故障";
}

std::string Urma1181Urma::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1181Urma::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1181Urma::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1181Urma::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1181Urma::GetId() const
{
    return "urma_1181";
}
} // namespace diag
