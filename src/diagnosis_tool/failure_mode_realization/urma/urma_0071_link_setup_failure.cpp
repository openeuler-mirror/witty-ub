#include "urma_0071_link_setup_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0071LinkSetupFailure> g_urma("urma_0071");

bool Urma0071LinkSetupFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {
        "urma_0072", "urma_0074", "urma_0076", "urma_0078", "urma_0080", "urma_0082", "urma_0086", "urma_0096",
        "urma_0099", "urma_0101", "urma_0105", "urma_0112", "urma_0114", "urma_0117", "urma_0119", "urma_0121",
        "urma_0123", "urma_0125", "urma_0127", "urma_0129", "urma_0133", "urma_0137", "urma_0139", "urma_0143",
        "urma_0147", "urma_0149", "urma_0151", "urma_0153", "urma_0155", "urma_0164", "urma_0168", "urma_0170",
        "urma_0172", "urma_0174", "urma_0176", "urma_0178", "urma_0180", "urma_0183", "urma_0186", "urma_0188",
        "urma_0190", "urma_0194", "urma_0196", "urma_0199", "urma_0203", "urma_0205", "urma_0207", "urma_0211",
        "urma_0213", "urma_0215", "urma_0218", "urma_0220", "urma_0222", "urma_0225", "urma_0228", "urma_0230",
        "urma_0232", "urma_0234", "urma_0236", "urma_0238", "urma_0240", "urma_0243", "urma_0245", "urma_0247",
        "urma_0249", "urma_0251", "urma_0253", "urma_0257", "urma_0262", "urma_0264", "urma_0266", "urma_0268",
        "urma_0270", "urma_0272", "urma_0278", "urma_0284", "urma_0286", "urma_0288", "urma_0292", "urma_0301",
        "urma_0304", "urma_0306", "urma_0312", "urma_0315", "urma_0317", "urma_0320", "urma_0323", "urma_0326",
        "urma_0334", "urma_0336", "urma_0338", "urma_0340", "urma_0342", "urma_0344", "urma_0348", "urma_0351",
        "urma_0354", "urma_0357", "urma_0359", "urma_0361", "urma_0365", "urma_0368", "urma_0371", "urma_0374",
        "urma_0376", "urma_0378", "urma_0380", "urma_0384", "urma_0386", "urma_0389", "urma_0392", "urma_0395",
        "urma_0398", "urma_0401", "urma_0404", "urma_0407", "urma_0410", "urma_0413", "urma_0421", "urma_0423",
        "urma_0427", "urma_0435", "urma_0438", "urma_0446", "urma_0449", "urma_0457", "urma_0459", "urma_0462",
        "urma_0466", "urma_0469", "urma_0472", "urma_0477", "urma_0483", "urma_0489", "urma_0495", "urma_0499",
        "urma_0501", "urma_0503", "urma_0505", "urma_0507", "urma_0509", "urma_0511", "urma_0513", "urma_0516",
        "urma_0519", "urma_0522", "urma_0524", "urma_0527", "urma_0530", "urma_0533", "urma_0541", "urma_0545",
        "urma_0550", "urma_0555", "urma_0559", "urma_0561", "urma_0563", "urma_0565", "urma_0567", "urma_0569",
        "urma_0571", "urma_0573", "urma_0576", "urma_0578", "urma_0585", "urma_0590", "urma_0596", "urma_0601",
        "urma_0603", "urma_0606", "urma_0609", "urma_0612", "urma_0618", "urma_0622", "urma_0626", "urma_0630",
        "urma_0635", "urma_0639", "urma_0643", "urma_0646", "urma_0649", "urma_0652", "urma_0656", "urma_0662",
        "urma_0668", "urma_0672", "urma_0675", "urma_0680", "urma_0685", "urma_0689", "urma_0693", "urma_0697",
        "urma_0701", "urma_0706", "urma_0713", "urma_0717", "urma_0719", "urma_0723", "urma_0729", "urma_0733",
        "urma_0737", "urma_0743", "urma_0747", "urma_0753", "urma_0755", "urma_0757", "urma_0761", "urma_0764",
        "urma_0768", "urma_0772", "urma_0775", "urma_0778", "urma_0781", "urma_0784", "urma_0786", "urma_0789",
        "urma_0791", "urma_0794", "urma_0797", "urma_0799", "urma_0802", "urma_0804", "urma_0806", "urma_0808",
        "urma_0810", "urma_0812", "urma_0814", "urma_0816", "urma_0818", "urma_0820", "urma_0828", "urma_0833",
        "urma_0838", "urma_0843", "urma_0845", "urma_0848", "urma_0851", "urma_0854", "urma_0857", "urma_0859",
        "urma_0862", "urma_0864", "urma_0867", "urma_0869", "urma_0872", "urma_0874", "urma_0876", "urma_0878",
        "urma_0880", "urma_0882", "urma_0884", "urma_0886"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0071LinkSetupFailure::GetName() const
{
    return "建链失败";
}

std::string Urma0071LinkSetupFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma0071LinkSetupFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0071LinkSetupFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0071LinkSetupFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0071LinkSetupFailure::GetId() const
{
    return "urma_0071";
}
} // namespace diag
